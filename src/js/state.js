// src/js/state.js — Global reactive state
(function() {
  const DEFAULT = {
    currentUser: null, currentPage: 'home',
    currentEmotion: 'neutral', emotionConfidence: 0,
    webcamStream: null, isDetecting: false,
    contentItems: [], currentContent: null,
    sessionStartTime: null, sessionTimerInterval: null,
    sessionDuration: 0, currentRating: 0
  };
  let state = { ...DEFAULT };
  let subs = [];

  function notify(changes) { subs.forEach(fn => fn(state, changes)); }

  const proxy = new Proxy(state, {
    set(t, k, v) { const old = t[k]; t[k] = v; notify({ [k]: { old, new: v } }); return true; },
    get(t, k)    { return t[k]; }
  });

  proxy.set = (k, v) => { proxy[k] = v; };
  proxy.subscribe = fn => { subs.push(fn); return () => { subs = subs.filter(s => s !== fn); }; };
  proxy.reset = () => { Object.assign(state, DEFAULT); notify({}); };
  proxy.getState = () => ({ ...state });

  window.AppState = proxy;
  console.log('AppState ready');
})();
