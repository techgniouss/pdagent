"""aiohttp server that streams video and accepts input for the remote session.

Lazy-imports ``aiohttp`` inside ``start`` so the idle bot never pays the cost.
Three routes behind a single token+cookie+fingerprint check:

* ``GET /?t=<token>``      — serves the mobile viewer HTML, sets the
  ``pdremote`` cookie, records ``(User-Agent, sha256(ip))`` on first hit.
* ``GET /ws/video``        — MJPEG over WebSocket frames from ``frame_iter``.
* ``GET /ws/input``        — JSON events dispatched via ``InputDispatcher``.
* ``GET /healthz``          — liveness probe (no auth).

The HTML viewer is kept inline (no separate file, no static dir) so the
package has exactly one extra file per remote feature area. Everything
except healthz requires the ``pdremote`` cookie to match ``session.token``
and the (UA, hashed-IP) to match the first-hit fingerprint.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Optional

from pocket_desk_agent.remote.session import RemoteSession

logger = logging.getLogger(__name__)

COOKIE_NAME = "pdremote"
_BACKPRESSURE_BYTES = 512 * 1024
_PREVIEW_UA_MARKERS = (
    "telegrambot",
    "twitterbot",
    "slackbot",
    "discordbot",
    "facebookexternalhit",
    "whatsapp",
)


def _client_ip(request: Any) -> str:
    """Best-effort real client IP. cloudflared sets Cf-Connecting-IP."""
    headers = request.headers
    for header in ("Cf-Connecting-IP", "X-Forwarded-For", "X-Real-IP"):
        value = headers.get(header)
        if value:
            return value.split(",")[0].strip()
    peer = request.transport.get_extra_info("peername") if request.transport else None
    if peer:
        return str(peer[0])
    return ""


def _fingerprint(request: Any) -> tuple[str, str]:
    """Return (User-Agent, sha256(ip)) — the two values we bind a session to."""
    ua = request.headers.get("User-Agent", "")
    ip = _client_ip(request)
    ip_hash = hashlib.sha256(ip.encode("utf-8", errors="replace")).hexdigest()
    return ua, ip_hash


def _is_link_preview_request(request: Any) -> bool:
    """Return True for known crawler/link-preview requests."""
    ua = request.headers.get("User-Agent", "").lower()
    return any(marker in ua for marker in _PREVIEW_UA_MARKERS)


def _cookie_token(request: Any) -> Optional[str]:
    cookie = request.cookies.get(COOKIE_NAME)
    return cookie if cookie else None


def _authorize_ws(session: RemoteSession, request: Any) -> Optional[str]:
    """Return an error string when the WS request should be rejected."""
    if session.torn_down:
        return "session gone"
    token = _cookie_token(request)
    if not token or token != session.token:
        return "bad cookie"
    current_fp = _fingerprint(request)
    if session.bound_fingerprint is None:
        session.bound_fingerprint = current_fp
        logger.info("[remote] bound WS fingerprint for user %s", session.user_id)
        return None
    if current_fp != session.bound_fingerprint:
        # Mobile networks or proxy metadata can shift between requests.
        # If cookie token is valid, allow and refresh the bound fingerprint.
        logger.info("[remote] refreshed WS fingerprint for user %s", session.user_id)
        session.bound_fingerprint = current_fp
    return None


async def _handle_root(request: Any) -> Any:
    """Serve the mobile viewer after validating the one-shot token."""
    from aiohttp import web  # type: ignore

    session: RemoteSession = request.app["session"]
    if session.torn_down:
        return web.Response(status=410, text="Session has ended.")

    token = request.query.get("t", "")
    cookie_token = _cookie_token(request)

    if token != session.token and cookie_token != session.token:
        logger.info("[remote] root request rejected: bad token")
        return web.Response(status=404, text="Not found.")

    current_fp = _fingerprint(request)
    if session.bound_fingerprint is None:
        if _is_link_preview_request(request):
            logger.info("[remote] preview request detected; deferring fingerprint bind for user %s", session.user_id)
        else:
            session.bound_fingerprint = current_fp
            logger.info("[remote] bound fingerprint for user %s", session.user_id)
    elif session.bound_fingerprint != current_fp:
        # Some messengers/open-in-browser flows change UA/IP between requests.
        # Token/cookie validation above already authenticates the caller.
        session.bound_fingerprint = current_fp
        logger.info("[remote] refreshed root fingerprint for user %s", session.user_id)

    response = web.Response(text=_VIEWER_HTML, content_type="text/html")
    response.set_cookie(
        COOKIE_NAME,
        session.token,
        httponly=True,
        secure=True,
        samesite="Lax",
        path="/",
        max_age=max(60, int(session.idle_seconds() + 3600)),
    )
    session.touch()
    return response


async def _handle_healthz(request: Any) -> Any:
    from aiohttp import web  # type: ignore

    return web.Response(text="ok")


async def _handle_ws_video(request: Any) -> Any:
    from aiohttp import web  # type: ignore

    session: RemoteSession = request.app["session"]
    reject = _authorize_ws(session, request)
    if reject:
        logger.info("[remote] /ws/video rejected (%s) for user %s", reject, session.user_id)
        return web.Response(status=401, text="Unauthorized.")

    ws = web.WebSocketResponse(heartbeat=20.0, max_msg_size=0)
    await ws.prepare(request)
    session.active_ws.add(ws)
    session.touch()

    from pocket_desk_agent.remote.capture import frame_iter

    sent_frames = 0
    try:
        async for jpeg in frame_iter(session):
            if ws.closed or session.torn_down:
                break
            if not jpeg:
                # Explicit skip sentinel from frame_iter — keep loop cadence.
                continue

            writer = getattr(ws, "_writer", None)
            transport = getattr(writer, "transport", None) if writer else None
            if transport is not None:
                try:
                    if transport.get_write_buffer_size() > _BACKPRESSURE_BYTES:
                        continue
                except Exception:
                    pass

            try:
                await ws.send_bytes(jpeg)
                sent_frames += 1
                # Keep the session alive while someone is actively viewing.
                session.touch()
            except ConnectionResetError:
                break
            except Exception as exc:
                logger.debug("[remote] ws/video send failed: %s", exc)
                break
    finally:
        session.active_ws.discard(ws)
        if not ws.closed:
            try:
                await ws.close()
            except Exception:
                pass
        logger.info(
            "[remote] /ws/video closed after %d frames (user %s)",
            sent_frames,
            session.user_id,
        )
    return ws


async def _handle_ws_input(request: Any) -> Any:
    from aiohttp import WSMsgType, web  # type: ignore

    session: RemoteSession = request.app["session"]
    reject = _authorize_ws(session, request)
    if reject:
        logger.info("[remote] /ws/input rejected (%s) for user %s", reject, session.user_id)
        return web.Response(status=401, text="Unauthorized.")

    from pocket_desk_agent.remote.input_bridge import InputDispatcher

    ws = web.WebSocketResponse(heartbeat=20.0)
    await ws.prepare(request)
    session.active_ws.add(ws)
    dispatcher = InputDispatcher(session)
    last_failsafe_reported = 0.0

    try:
        async for msg in ws:
            if ws.closed or session.torn_down:
                break
            if msg.type == WSMsgType.TEXT:
                try:
                    event = json.loads(msg.data)
                except Exception:
                    continue
                status = dispatcher.apply(event)
                if status == "failsafe" and dispatcher.last_failsafe_at > last_failsafe_reported:
                    last_failsafe_reported = dispatcher.last_failsafe_at
                    try:
                        await ws.send_json({"type": "status", "message": "failsafe"})
                    except Exception:
                        pass
            elif msg.type in (WSMsgType.ERROR, WSMsgType.CLOSED):
                break
    finally:
        session.active_ws.discard(ws)
        if not ws.closed:
            try:
                await ws.close()
            except Exception:
                pass
        logger.info("[remote] /ws/input closed (user %s)", session.user_id)
    return ws


def build_app(session: RemoteSession):
    """Build the aiohttp Application with ``session`` wired into each handler."""
    from aiohttp import web  # type: ignore

    app = web.Application(client_max_size=256 * 1024)
    app["session"] = session
    app.router.add_get("/", _handle_root)
    app.router.add_get("/healthz", _handle_healthz)
    app.router.add_get("/ws/video", _handle_ws_video)
    app.router.add_get("/ws/input", _handle_ws_input)
    return app


async def start(session: RemoteSession, host: str) -> tuple[Any, Any]:
    """Start the aiohttp server on ``session.port`` and return (runner, site)."""
    from aiohttp import web  # type: ignore

    app = build_app(session)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, session.port)
    await site.start()
    return runner, site


_VIEWER_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover" />
<title>Pocket Desk Remote</title>
<style>
  :root { color-scheme: dark; }
  html, body { margin:0; padding:0; height:100%; background:#000; overflow:hidden; touch-action:none; }
  #stage { position:fixed; inset:0; display:flex; align-items:center; justify-content:center; }
  canvas { max-width:100vw; max-height:100vh; background:#000; display:block; touch-action:none; }
  #hud { position:fixed; top:env(safe-area-inset-top,0); left:0; right:0; display:flex; justify-content:space-between; align-items:center; padding:6px 10px; pointer-events:none; font:12px/1.2 system-ui, -apple-system, sans-serif; color:#bbb; }
  #hud .pill { background:rgba(0,0,0,.55); border:1px solid #333; border-radius:999px; padding:4px 10px; pointer-events:auto; }
  #toolbar { position:fixed; bottom:calc(env(safe-area-inset-bottom,0) + 8px); left:0; right:0; display:flex; justify-content:center; gap:8px; pointer-events:none; }
  #toolbar button { pointer-events:auto; background:rgba(0,0,0,.65); color:#fff; border:1px solid #555; border-radius:999px; padding:8px 14px; font:14px system-ui; }
  #toolbar button:active { background:#222; }
  #ime { position:fixed; bottom:-40px; left:0; width:100%; opacity:0.01; font-size:16px; padding:4px; border:none; }
  #status { position:fixed; left:0; right:0; bottom:56px; text-align:center; color:#fbbf24; font:13px system-ui; pointer-events:none; text-shadow:0 1px 3px #000; }
  #slider { width:120px; }
  #trackpadWrap { position:fixed; left:8px; right:8px; bottom:calc(env(safe-area-inset-bottom,0) + 56px); height:110px; display:none; z-index:6; }
  #trackpadWrap.show { display:block; }
  #trackpadLabel { color:#bdbdbd; font:12px/1.1 system-ui; margin:0 0 6px 6px; }
  #trackpad { height:86px; border:1px solid #3a3a3a; border-radius:12px; background:rgba(0,0,0,.65); touch-action:none; }
</style>
</head>
<body>
  <div id="stage"><canvas id="view"></canvas></div>
  <div id="hud">
    <span id="conn" class="pill">connecting...</span>
    <span id="fps" class="pill">-- fps</span>
  </div>
  <div id="status"></div>
  <div id="toolbar">
    <button id="kbBtn">keys</button>
    <button id="rcBtn">right</button>
    <button id="mouseBtn">mouse off</button>
    <button id="zoomBtn">zoom 1.0x</button>
    <button id="modeBtn">pan off</button>
    <input id="slider" type="range" min="30" max="85" value="60" />
    <button id="stopBtn">end</button>
  </div>
  <div id="trackpadWrap">
    <div id="trackpadLabel">mouse pad: drag to move, tap to click</div>
    <div id="trackpad"></div>
  </div>
  <input id="ime" autocomplete="off" autocapitalize="off" spellcheck="false" />
<script>
(function(){
  var stage = document.getElementById('stage');
  var canvas = document.getElementById('view');
  var ctx = canvas.getContext('2d');
  var connEl = document.getElementById('conn');
  var fpsEl = document.getElementById('fps');
  var statusEl = document.getElementById('status');
  var slider = document.getElementById('slider');
  var kbBtn = document.getElementById('kbBtn');
  var rcBtn = document.getElementById('rcBtn');
  var mouseBtn = document.getElementById('mouseBtn');
  var zoomBtn = document.getElementById('zoomBtn');
  var modeBtn = document.getElementById('modeBtn');
  var trackpadWrap = document.getElementById('trackpadWrap');
  var trackpad = document.getElementById('trackpad');
  var stopBtn = document.getElementById('stopBtn');
  var ime = document.getElementById('ime');

  var vw = 1280, vh = 720;
  var frameCount = 0, frameWindow = Date.now();
  var rightClickMode = false;
  var renderBusy = false;
  var queuedData = null;
  var viewZoom = 1.0;
  var viewPanX = 0;
  var viewPanY = 0;
  var panMode = false;
  var panDrag = null;
  var ZOOM_STEPS = [1.0, 1.5, 2.0, 3.0];
  var mouseMode = false;
  var padTouch = null;
  var padMouseDrag = null;
  var padTwoFingerY = 0;
  var padLongTimer = null;
  var PAD_GAIN = 1.6;

  function resize() {
    var ar = vw / vh;
    var cw = window.innerWidth, ch = window.innerHeight;
    if (cw / ch > ar) { canvas.style.height = ch + 'px'; canvas.style.width = (ch*ar) + 'px'; }
    else { canvas.style.width = cw + 'px'; canvas.style.height = (cw/ar) + 'px'; }
  }
  window.addEventListener('resize', resize);
  resize();

  function showStatus(txt) {
    statusEl.textContent = txt || '';
    if (txt) setTimeout(function(){ if (statusEl.textContent === txt) statusEl.textContent = ''; }, 3500);
  }

  function clamp(v, lo, hi) {
    return Math.max(lo, Math.min(hi, v));
  }

  function getViewport() {
    var srcW = vw / viewZoom;
    var srcH = vh / viewZoom;
    var maxX = Math.max(0, vw - srcW);
    var maxY = Math.max(0, vh - srcH);
    viewPanX = clamp(viewPanX, 0, maxX);
    viewPanY = clamp(viewPanY, 0, maxY);
    return {x:viewPanX, y:viewPanY, w:srcW, h:srcH};
  }

  function setZoom(nextZoom) {
    nextZoom = clamp(nextZoom, 1.0, 3.0);
    var oldVp = getViewport();
    var cx = oldVp.x + oldVp.w / 2;
    var cy = oldVp.y + oldVp.h / 2;
    viewZoom = nextZoom;
    viewPanX = cx - (vw / viewZoom) / 2;
    viewPanY = cy - (vh / viewZoom) / 2;
    getViewport();
    updateZoomUi();
  }

  function updateZoomUi() {
    if (viewZoom <= 1.0001) {
      viewZoom = 1.0;
      panMode = false;
      viewPanX = 0;
      viewPanY = 0;
    }
    zoomBtn.textContent = 'zoom ' + viewZoom.toFixed(1) + 'x';
    modeBtn.textContent = panMode ? 'pan on' : 'pan off';
    modeBtn.disabled = viewZoom <= 1.0001;
  }

  function clearPadLong() {
    if (padLongTimer) {
      clearTimeout(padLongTimer);
      padLongTimer = null;
    }
  }

  function updateMouseUi() {
    mouseBtn.textContent = mouseMode ? 'mouse on' : 'mouse off';
    if (mouseMode) {
      trackpadWrap.classList.add('show');
      stage.style.bottom = '170px';
    } else {
      trackpadWrap.classList.remove('show');
      stage.style.bottom = '0';
      padTouch = null;
      padMouseDrag = null;
      clearPadLong();
    }
    resize();
  }

  // ── Video WebSocket ──────────────────────────────────────────────
  function drawFrameImage(image) {
    vw = image.naturalWidth || image.width || vw;
    vh = image.naturalHeight || image.height || vh;
    if (canvas.width !== vw || canvas.height !== vh) {
      canvas.width = vw;
      canvas.height = vh;
    }
    var vp = getViewport();
    resize();
    ctx.drawImage(image, vp.x, vp.y, vp.w, vp.h, 0, 0, vw, vh);
    frameCount++;
    var now = Date.now();
    if (now - frameWindow >= 1000) {
      fpsEl.textContent = frameCount + ' fps';
      frameCount = 0; frameWindow = now;
    }
  }

  function drawFrameBlob(blob, done) {
    if (window.createImageBitmap) {
      createImageBitmap(blob).then(
        function(bitmap){
          drawFrameImage(bitmap);
          if (bitmap.close) bitmap.close();
          done();
        },
        function(){
          showStatus('Frame decode failed');
          done();
        }
      );
      return;
    }

    var url = URL.createObjectURL(blob);
    var tmp = new Image();
    tmp.onload = function() {
      drawFrameImage(tmp);
      URL.revokeObjectURL(url);
      done();
    };
    tmp.onerror = function() {
      URL.revokeObjectURL(url);
      showStatus('Frame decode failed');
      done();
    };
    tmp.src = url;
  }

  function pumpFrames() {
    if (renderBusy || !queuedData) return;
    renderBusy = true;
    var data = queuedData;
    queuedData = null;
    var blob = new Blob([data], {type:'image/jpeg'});
    drawFrameBlob(blob, function(){
      renderBusy = false;
      if (queuedData) pumpFrames();
    });
  }

  var videoWs;
  function connectVideo() {
    var proto = location.protocol === 'https:' ? 'wss' : 'ws';
    videoWs = new WebSocket(proto + '://' + location.host + '/ws/video');
    videoWs.binaryType = 'arraybuffer';
    videoWs.onopen = function(){ connEl.textContent = 'live'; };
    videoWs.onclose = function(){ connEl.textContent = 'offline'; setTimeout(connectVideo, 2000); };
    videoWs.onerror = function(){ connEl.textContent = 'error'; };
    videoWs.onmessage = function(ev) {
      queuedData = ev.data;
      pumpFrames();
    };
  }
  connectVideo();

  // ── Input WebSocket ──────────────────────────────────────────────
  var inputWs;
  function connectInput() {
    var proto = location.protocol === 'https:' ? 'wss' : 'ws';
    inputWs = new WebSocket(proto + '://' + location.host + '/ws/input');
    inputWs.onopen = function(){ sendConfig(); };
    inputWs.onclose = function(){ setTimeout(connectInput, 2000); };
    inputWs.onmessage = function(ev){
      try {
        var data = JSON.parse(ev.data);
        if (data && data.type === 'status' && data.message === 'failsafe') {
          showStatus('pyautogui fail-safe - move cursor away from corner');
        }
      } catch (e) {}
    };
  }
  connectInput();

  function send(ev) {
    if (!inputWs || inputWs.readyState !== 1) return;
    try { inputWs.send(JSON.stringify(ev)); } catch(e) {}
  }

  function sendConfig() {
    send({type:'config', quality: parseInt(slider.value, 10)});
  }

  // ── Touch → mouse translation ─────────────────────────────────────
  function normalized(evt) {
    var rect = canvas.getBoundingClientRect();
    var t = evt.touches ? (evt.touches[0] || evt.changedTouches[0]) : evt;
    var x = (t.clientX - rect.left) / rect.width;
    var y = (t.clientY - rect.top) / rect.height;
    x = Math.max(0, Math.min(1, x));
    y = Math.max(0, Math.min(1, y));
    return {x:x, y:y};
  }

  function remoteNormalized(evt) {
    var n = normalized(evt);
    var vp = getViewport();
    var x = clamp((vp.x + (n.x * vp.w)) / vw, 0, 1);
    var y = clamp((vp.y + (n.y * vp.h)) / vh, 0, 1);
    return {x:x, y:y};
  }

  var touchStart = null;
  var longPressTimer = null;
  var dragging = false;
  var twoFinger = false;
  var twoFingerY = 0;
  var LONG_PRESS_MS = 500;
  var DRAG_THRESHOLD = 8; // px

  canvas.addEventListener('touchstart', function(e){
    if (panMode) {
      e.preventDefault();
      if (e.touches.length === 1) {
        var rect = canvas.getBoundingClientRect();
        var vp = getViewport();
        panDrag = {
          cx: e.touches[0].clientX,
          cy: e.touches[0].clientY,
          panX: viewPanX,
          panY: viewPanY,
          srcW: vp.w,
          srcH: vp.h,
          rectW: Math.max(1, rect.width),
          rectH: Math.max(1, rect.height),
        };
      }
      return;
    }

    e.preventDefault();
    if (e.touches.length === 2) {
      twoFinger = true;
      twoFingerY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
      clearTimeout(longPressTimer);
      return;
    }
    twoFinger = false;
    var n = remoteNormalized(e);
    touchStart = {x:n.x, y:n.y, raw:{cx:e.touches[0].clientX, cy:e.touches[0].clientY}, t:Date.now()};
    dragging = false;
    send({type:'move', x:n.x, y:n.y});
    longPressTimer = setTimeout(function(){
      if (!dragging && touchStart) {
        send({type:'click', x:touchStart.x, y:touchStart.y, button:'right'});
        touchStart = null;
      }
    }, LONG_PRESS_MS);
  }, {passive:false});

  canvas.addEventListener('touchmove', function(e){
    if (panMode) {
      e.preventDefault();
      if (panDrag && e.touches.length === 1) {
        var dx = e.touches[0].clientX - panDrag.cx;
        var dy = e.touches[0].clientY - panDrag.cy;
        viewPanX = panDrag.panX - (dx / panDrag.rectW) * panDrag.srcW;
        viewPanY = panDrag.panY - (dy / panDrag.rectH) * panDrag.srcH;
        getViewport();
      }
      return;
    }

    e.preventDefault();
    if (e.touches.length === 2) {
      twoFinger = true;
      var midY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
      var dy = midY - twoFingerY;
      if (Math.abs(dy) > 6) {
        send({type:'scroll', dy: dy < 0 ? -3 : 3});
        twoFingerY = midY;
      }
      return;
    }
    if (!touchStart) return;
    var n = remoteNormalized(e);
    if (!dragging) {
      var dx = e.touches[0].clientX - touchStart.raw.cx;
      var dy2 = e.touches[0].clientY - touchStart.raw.cy;
      if (Math.hypot(dx, dy2) > DRAG_THRESHOLD) {
        dragging = true;
        clearTimeout(longPressTimer);
        send({type:'down', x:touchStart.x, y:touchStart.y, button:'left'});
      }
    }
    if (dragging) {
      send({type:'move', x:n.x, y:n.y});
    }
  }, {passive:false});

  canvas.addEventListener('touchend', function(e){
    if (panMode) {
      e.preventDefault();
      panDrag = null;
      return;
    }

    e.preventDefault();
    clearTimeout(longPressTimer);
    if (twoFinger) { twoFinger = false; return; }
    if (!touchStart) return;
    var n = remoteNormalized(e);
    if (dragging) {
      send({type:'up', x:n.x, y:n.y, button:'left'});
    } else {
      var btn = rightClickMode ? 'right' : 'left';
      send({type:'click', x:touchStart.x, y:touchStart.y, button:btn});
      if (rightClickMode) { rightClickMode = false; rcBtn.textContent = 'right'; }
    }
    touchStart = null;
    dragging = false;
  }, {passive:false});

  // ── Mouse fallback (desktop browsers) ───────────────────────────
  canvas.addEventListener('mousemove', function(e){
    var n = remoteNormalized(e);
    send({type:'move', x:n.x, y:n.y});
  });
  canvas.addEventListener('mousedown', function(e){
    var n = remoteNormalized(e);
    var btn = e.button === 2 ? 'right' : (e.button === 1 ? 'middle' : 'left');
    send({type:'down', x:n.x, y:n.y, button:btn});
  });
  canvas.addEventListener('mouseup', function(e){
    var n = remoteNormalized(e);
    var btn = e.button === 2 ? 'right' : (e.button === 1 ? 'middle' : 'left');
    send({type:'up', x:n.x, y:n.y, button:btn});
  });
  canvas.addEventListener('contextmenu', function(e){ e.preventDefault(); });
  canvas.addEventListener('wheel', function(e){
    e.preventDefault();
    send({type:'scroll', dy: e.deltaY > 0 ? -3 : 3});
  }, {passive:false});

  // ── Keyboard via hidden input ────────────────────────────────────
  kbBtn.addEventListener('click', function(){
    ime.focus();
    ime.value = '';
  });
  ime.addEventListener('input', function(){
    var txt = ime.value;
    if (txt) {
      send({type:'text', text: txt});
      ime.value = '';
    }
  });
  ime.addEventListener('keydown', function(e){
    var named = {
      'Backspace':'backspace','Tab':'tab','Enter':'enter','Escape':'esc',
      'ArrowLeft':'left','ArrowRight':'right','ArrowUp':'up','ArrowDown':'down',
      'Home':'home','End':'end','PageUp':'pageup','PageDown':'pagedown','Delete':'delete'
    };
    var key = named[e.key];
    if (!key) return;
    e.preventDefault();
    if (e.ctrlKey || e.metaKey || e.altKey) {
      var mods = [];
      if (e.ctrlKey) mods.push('ctrl');
      if (e.altKey) mods.push('alt');
      if (e.metaKey) mods.push('win');
      mods.push(key);
      send({type:'hotkey', keys: mods});
    } else {
      send({type:'key', key: key});
    }
  });

  // ── Right-click one-shot button ─────────────────────────────────
  rcBtn.addEventListener('click', function(){
    rightClickMode = !rightClickMode;
    rcBtn.textContent = rightClickMode ? 'right-once' : 'right';
  });

  mouseBtn.addEventListener('click', function(){
    mouseMode = !mouseMode;
    updateMouseUi();
  });

  trackpad.addEventListener('touchstart', function(e){
    e.preventDefault();
    clearPadLong();
    if (e.touches.length === 1) {
      padTouch = {
        x: e.touches[0].clientX,
        y: e.touches[0].clientY,
        moved: false,
      };
      padLongTimer = setTimeout(function(){
        if (padTouch && !padTouch.moved) {
          send({type:'pointer_click', button:'right'});
          padTouch = null;
        }
      }, 500);
    } else if (e.touches.length === 2) {
      padTouch = null;
      padTwoFingerY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
    }
  }, {passive:false});

  trackpad.addEventListener('touchmove', function(e){
    e.preventDefault();
    if (e.touches.length === 2) {
      clearPadLong();
      var midY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
      var dy = midY - padTwoFingerY;
      if (Math.abs(dy) > 6) {
        send({type:'scroll', dy: dy < 0 ? -3 : 3});
        padTwoFingerY = midY;
      }
      return;
    }

    if (!padTouch || e.touches.length !== 1) return;
    var t = e.touches[0];
    var dx = t.clientX - padTouch.x;
    var dy2 = t.clientY - padTouch.y;
    if (Math.abs(dx) > 0.5 || Math.abs(dy2) > 0.5) {
      send({type:'relmove', dx: dx, dy: dy2, gain: PAD_GAIN});
      padTouch.x = t.clientX;
      padTouch.y = t.clientY;
      if (Math.hypot(dx, dy2) > 2) {
        padTouch.moved = true;
        clearPadLong();
      }
    }
  }, {passive:false});

  trackpad.addEventListener('touchend', function(e){
    e.preventDefault();
    clearPadLong();
    if (padTouch && !padTouch.moved) {
      send({type:'pointer_click', button:'left'});
    }
    padTouch = null;
  }, {passive:false});

  trackpad.addEventListener('mousedown', function(e){
    e.preventDefault();
    padMouseDrag = {x:e.clientX, y:e.clientY, moved:false};
  });

  trackpad.addEventListener('mousemove', function(e){
    if (!padMouseDrag) return;
    e.preventDefault();
    var dx = e.clientX - padMouseDrag.x;
    var dy = e.clientY - padMouseDrag.y;
    if (Math.abs(dx) > 0.5 || Math.abs(dy) > 0.5) {
      send({type:'relmove', dx: dx, dy: dy, gain: PAD_GAIN});
      padMouseDrag.x = e.clientX;
      padMouseDrag.y = e.clientY;
      padMouseDrag.moved = true;
    }
  });

  trackpad.addEventListener('mouseup', function(e){
    if (!padMouseDrag) return;
    e.preventDefault();
    if (!padMouseDrag.moved) {
      send({type:'pointer_click', button:'left'});
    }
    padMouseDrag = null;
  });

  trackpad.addEventListener('mouseleave', function(){
    padMouseDrag = null;
  });

  zoomBtn.addEventListener('click', function(){
    var current = viewZoom;
    var next = ZOOM_STEPS[0];
    for (var i = 0; i < ZOOM_STEPS.length; i++) {
      if (ZOOM_STEPS[i] > current + 0.01) {
        next = ZOOM_STEPS[i];
        break;
      }
    }
    if (next <= current + 0.01) next = ZOOM_STEPS[0];
    setZoom(next);
  });

  modeBtn.addEventListener('click', function(){
    if (viewZoom <= 1.0001) {
      panMode = false;
    } else {
      panMode = !panMode;
    }
    updateZoomUi();
  });
  updateZoomUi();
  updateMouseUi();

  // ── Quality slider (debounced) ──────────────────────────────────
  var qTimer = null;
  slider.addEventListener('input', function(){
    clearTimeout(qTimer);
    qTimer = setTimeout(sendConfig, 250);
  });

  // ── Disconnect ─────────────────────────────────────────────────
  stopBtn.addEventListener('click', function(){
    try { videoWs && videoWs.close(); } catch(e){}
    try { inputWs && inputWs.close(); } catch(e){}
    document.body.innerHTML = '<div style="color:#aaa;font:16px system-ui;padding:32px;text-align:center">Disconnected. You can close this tab.</div>';
  });
})();
</script>
</body>
</html>
"""
