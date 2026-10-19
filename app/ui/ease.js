// ../pub-game-store/native/ui/ease.js
// reconstructed from the esbuild bundle in eboot.bin


  var EASE_OUT = [0.16, 1, 0.3, 1];
  // A focused card's 6 px lift. EASE_OUT covers five of its pixels in the first frames and the sixth well
  // after, which reads as the card rising and then jerking up again; this curve spaces the pixels evenly.
  var LIFT = { type: "tween", duration: 0.22, ease: [0.25, 0.46, 0.45, 0.94] };

export { EASE_OUT, LIFT };
