loadScript('/js/frames/hearthstone.js').then(() => {
    Hearthstone.showControls();
    loadFramePacks([
        {name:'Hearthstone Minions', value:'HearthstoneMinion'},
        {name:'Hearthstone Spells', value:'HearthstoneSpell'}
    ]);
});
