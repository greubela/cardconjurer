loadScript('/js/frames/hearthstone.js').then(() => {
    Hearthstone.showControls();
    loadFramePacks(Hearthstone.packs);
});
