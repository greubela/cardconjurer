/* Hearthstone extension. Uses the existing frame, text, art and save APIs. */
var Hearthstone = window.Hearthstone || (() => {
    const root = '/img/frames/hearthstone/';
    const classes = ['neutral','deathknight','demonhunter','druid','hunter','mage','paladin','priest','rogue','shaman','warlock','warrior'];
    const labels = {deathknight:'Death Knight', demonhunter:'Demon Hunter'};
    const label = value => labels[value] || value[0].toUpperCase()+value.slice(1);
    const defaults = {class:'neutral', rarity:'none', bleed:false, body:true, portrait:true, scroll:true, name:true, mana:true, power:true, toughness:true, type:true, dragon:true};
    let kind = 'minion';
    let busy = false;
    let fontPromise;
    const frame = (name, file, extra={}) => ({name, src:root+file+'.png', hearthstone:true, ...extra});
    const background = k => frame('Hearthstone Black Surround / Bleed', k+'-black-surround', {
        bounds:{x:-0.05,y:-1/28,width:1.1,height:15/14}
    });
    function fonts() {
        if (!fontPromise) {
            fontPromise = Promise.all([
                ['hearthstone-title','GBJenLei-Medium.woff2'],
                ['hearthstone-rules','FranklinGothic-MediumCond.woff2']
            ].map(async ([name,file]) => {
                const font = new FontFace(name, `url(/fonts/hearthstone/${file})`);
                document.fonts.add(await font.load());
            }));
        }
        return fontPromise;
    }
    const settings = () => ({...defaults, ...(card.hearthstone || {})});
    function showControls() {
        let panel = document.getElementById('hearthstone-controls');
        if (!panel) {
            panel = document.createElement('div');
            panel.id = 'hearthstone-controls';
            panel.className = 'readable-background margin-bottom padding';
            panel.innerHTML = `<h3>Hearthstone components</h3>
                <div class="input-grid margin-bottom">
                    <label>Class<select id="hs-class" class="input" aria-label="Hearthstone class">${classes.map(c=>`<option value="${c}">${label(c)}</option>`).join('')}</select></label>
                    <label>Rarity<select id="hs-rarity" class="input" aria-label="Hearthstone rarity">${['none','common','rare','epic','legendary'].map(r=>`<option value="${r}">${label(r)}</option>`).join('')}</select></label>
                </div>
                <div class="input-grid margin-bottom">${[
                    ['body','Class body'],['portrait','Art border'],['scroll','Text scroll'],['name','Name ribbon'],
                    ['mana','Mana crystal'],['power','Power symbol'],['toughness','Toughness symbol'],
                    ['type','Type indicator'],['dragon','Legendary dragon'],['bleed','1/8-inch black margins']
                ].map(([id,text])=>`<label><input id="hs-${id}" type="checkbox"> ${text}</label>`).join('')}</div>
                <button id="hs-build" class="input">Build / replace Hearthstone layers</button>
                <p class="input-description">Build a complete card, then edit or remove each layer below. Class and component changes apply when you build. Text and art are preserved. Use the Text tab for cost, power, toughness and type (e.g. Beast). MtG codes such as {t}, {w}, {u} and {b} work in rules text.</p>`;
            document.querySelector('#creator-menu-frame > div').after(panel);
            panel.querySelector('#hs-build').onclick = build;
            document.querySelector('#selectFrameGroup').addEventListener('change', () => {
                panel.hidden = document.querySelector('#selectFrameGroup').value !== 'Hearthstone';
            });
        }
        panel.hidden = false;
        const state = settings();
        Object.keys(defaults).forEach(key => {
            const input = document.getElementById('hs-'+key);
            if (input.type==='checkbox') input.checked=state[key];
            else input.value=state[key];
        });
        return panel;
    }
    function readControls() {
        const state = {};
        Object.keys(defaults).forEach(key => {
            const input=document.getElementById('hs-'+key);
            state[key]=input.type==='checkbox' ? input.checked : input.value;
        });
        return state;
    }
    async function version(k, state=settings()) {
        await fonts();
        const bleed = state.bleed;
        await resetCardIrregularities({canvas:[getStandardWidth(),getStandardHeight(),bleed?0.05:0,bleed?1/28:0]});
        card.version = 'hearthstone-'+k;
        card.onload = '/js/frames/hearthstone.js';
        card.hearthstone = {...state,kind:k};
        card.margins = bleed;
        card.noCorners = true;
        document.getElementById('rounded-corners').checked = false;
        card.showsFlavorBar = false;
        drawTextBetweenFrames = false;
        card.artBounds = k==='minion'
            ? {x:117/460,y:67/644,width:228/460,height:316/644}
            : {x:94/460,y:83/644,width:278/460,height:310/644};
        autoFitArt();
        card.setSymbolBounds={x:-1,y:-1,width:0.01,height:0.01};
        resetSetSymbol();
        card.watermarkBounds={x:0.5,y:0.75,width:0.45,height:0.17};
        resetWatermark();
        const box=(name,x,y,w,h,size,extra={})=>({name,text:'',x:(x-20)/460,y:y/644,width:w/460,height:h/644,size:size/644,...extra});
        const display={font:'hearthstone-title',color:'white',outlineWidth:2/644,outlineColor:'#241c18',oneLine:true,align:'center'};
        loadTextOptions({
            title:box('Title',98,k==='minion'?337:343,302,45,29,{...display,rotation:-3}),
            mana:box('Mana cost',45,67,88,75,65,display),
            type:box('Type / tribe',153,557,204,29,21,display),
            rules:box('Rules Text',116,k==='minion'?423:435,270,k==='minion'?124:112,27,{font:'hearthstone-rules',align:'center',justify:'center',lineSpacing:0.05}),
            power:box('Power',44,530,90,78,57,display),
            toughness:box('Toughness',366,535,80,78,57,display)
        });
        await loadBottomInfo({credit:{text:'{elemidinfo-artist}',x:0.12,y:0.97,width:0.76,height:0.018,size:0.013,font:'mplantin',color:'white',align:'center',oneLine:true}});
        drawFrames();
    }
    function loadPack(k, restoring=false) {
        kind=k;
        showControls();
        availableFrames = [
            ...classes.flatMap(c=>[
                frame(label(c)+' '+label(k)+' Class Body',c+'-'+k+'-body'),
                frame(label(c)+' '+(k==='minion'?'Oval Art Border':'Spell Art Border'),c+'-'+k+'-portrait')
            ]),
            frame('Mana Crystal','mana-crystal'),
            frame('Text Scroll',k+'-description-area'),
            frame('Name Ribbon',k+'-name'),
            frame('Power Symbol (Sword)','power-symbol'),
            frame('Toughness Symbol (Health)','toughness-symbol'),
            frame('Type Indicator',k+'-kind'),
            frame('Legendary Dragon ('+k+'-dragon)',k+'-dragon'),
            frame('Rarity Socket',k+'-rarity-mask'),
            ...['common','rare','epic','legendary'].map(r=>frame(label(r)+' Rarity Gem',k+'-'+r)),
            background(k)
        ];
        document.querySelector('#loadFrameVersion').disabled=false;
        document.querySelector('#loadFrameVersion').onclick=()=>version(k);
        const loadVersion=document.querySelector('#loadFrameVersion').onclick;
        if(restoring) document.querySelector('#loadFrameVersion').onclick=()=>{};
        loadFramePack();
        document.querySelector('#loadFrameVersion').onclick=loadVersion;
    }
    async function build() {
        if (busy) return;
        busy=true;
        const button=document.getElementById('hs-build');
        button.disabled=true;
        try {
            const state=readControls();
            await version(kind,state);
            // Retain other styles' layers: this action replaces only our own parts.
            const retained=card.frames.filter(f=>!f.hearthstone);
            card.frames=[];
            document.getElementById('frame-list').innerHTML='';
            const layers=[background(kind)];
            const add=(enabled,name,file)=>{if(enabled) layers.push(frame(name,file));};
            add(state.body,label(state.class)+' Class Body',state.class+'-'+kind+'-body');
            add(state.portrait,label(state.class)+' Art Border',state.class+'-'+kind+'-portrait');
            add(state.scroll,'Text Scroll',kind+'-description-area');
            if(state.rarity!=='none') {
                add(true,'Rarity Socket',kind+'-rarity-mask');
                add(true,label(state.rarity)+' Rarity Gem',kind+'-'+state.rarity);
            }
            add(state.name,'Name Ribbon',kind+'-name');
            add(state.mana,'Mana Crystal','mana-crystal');
            add(state.power&&kind==='minion','Power Symbol (Sword)','power-symbol');
            add(state.toughness&&kind==='minion','Toughness Symbol (Health)','toughness-symbol');
            add(state.type,'Type Indicator',kind+'-kind');
            add(state.dragon&&state.rarity==='legendary','Legendary Dragon ('+kind+'-dragon)',kind+'-dragon');
            // addFrame's loading API creates images/UI; the caller owns array order.
            card.frames=[...layers.reverse().map(f=>({...f,masks:[]})),...retained];
            for(const f of card.frames.slice().reverse()) await addFrame([],f);
            await Promise.all(card.frames.map(f=>f.image.decode().catch(()=>{})));
            drawFrames();
        } finally {busy=false;button.disabled=false;}
    }
    async function restore() {
        await fonts();
        if(!card.version.startsWith('hearthstone-')) return;
        kind=card.hearthstone?.kind || card.version.slice('hearthstone-'.length);
        // Loading a save must not reset text, component positions, art or margins.
        document.querySelector('#selectFrameGroup').value='Hearthstone';
        showControls();
        const select=document.querySelector('#selectFramePack');
        select.innerHTML='<option value="HearthstoneMinion">Hearthstone Minions</option><option value="HearthstoneSpell">Hearthstone Spells</option>';
        select.value=kind==='spell'?'HearthstoneSpell':'HearthstoneMinion';
        loadPack(kind,true);
        drawTextBuffer();
        drawFrames();
    }
    return {showControls,loadPack,version,build,restore};
})();
if(card.version.startsWith('hearthstone-')) Hearthstone.restore();
