/* Hearthstone extension. Uses the existing frame, text, art and save APIs. */
var Hearthstone = window.Hearthstone || (() => {
    const root = '/img/frames/hearthstone/';
    const classes = ['neutral','deathknight','demonhunter','druid','hunter','mage','paladin','priest','rogue','shaman','warlock','warrior'];
    const labels = {deathknight:'Death Knight', demonhunter:'Demon Hunter'};
    const label = value => labels[value] || value[0].toUpperCase()+value.slice(1);
    const defaults = {tier:true,level:'1',class:'neutral', rarity:'none', bleed:false, body:true, portrait:true, scroll:true, name:true, mana:true, power:true, toughness:true, type:true, dragon:true};
    const types = {
        minion:{name:'Minions',pack:'HearthstoneMinion',frame:'minion',left:'Power',right:'Toughness',rightKey:'toughness',type:true,mana:'mana-crystal',leftIcon:'power-symbol',rightIcon:'toughness-symbol',art:[117,67,228,316],rules:[116,423,270,124]},
        spell:{name:'Spells',pack:'HearthstoneSpell',frame:'spell',type:true,mana:'mana-crystal',art:[84,112,291,240],rules:[116,435,270,112]},
        weapon:{name:'Weapons',pack:'HearthstoneWeapon',frame:'weapon',left:'Attack',right:'Durability',rightKey:'durability',type:true,typeDefault:false,mana:'mana-crystal',leftIcon:'weapon-power-symbol',rightIcon:'durability-symbol',art:[105,96,255,256],rules:[116,430,270,120],rulesColor:'white'},
        hero:{name:'Heroes',pack:'HearthstoneHero',frame:'hero',right:'Armor',rightKey:'armor',mana:'mana-crystal',rightIcon:'armor-symbol',art:[124,86,213,244],rules:[116,420,270,128]},
        location:{name:'Locations',pack:'HearthstoneLocation',frame:'location',right:'Durability',rightKey:'durability',mana:'location-mana-crystal',rightIcon:'location-durability-symbol',art:[67,66,326,281],rules:[116,442,270,120]},
        'hero-power':{name:'Hero Powers',pack:'HearthstoneHeroPower',frame:'hero-power',universal:true,noRarity:true,mana:'hero-power-mana-crystal',art:[158,142,149,139],rules:[116,424,270,130]},
        'battleground-minion':{name:'Battlegrounds Minions',pack:'HearthstoneBattlegroundMinion',frame:'minion',left:'Power',right:'Toughness',rightKey:'toughness',type:true,tier:true,leftIcon:'power-symbol',rightIcon:'toughness-symbol',art:[117,67,228,316],rules:[116,423,270,124]}
    };
    const packs=Object.values(types).map(t=>({name:'Hearthstone '+t.name,value:t.pack}));
    const profile=k=>types[k];
    const classPart=(k,c,part)=>profile(k).universal?'hero-power-'+part:c+'-'+profile(k).frame+'-'+part;
    let kind = 'minion';
    let busy = false;
    let fontPromise;
    const frame = (name, file, extra={}) => ({name, src:root+file+'.png', hearthstone:true, ...extra});
    const background = k => frame('Hearthstone Black Surround / Bleed', profile(k).frame+'-black-surround', {
        bounds:{x:-0.05,y:-1/28,width:1.1,height:15/14}
    });
    function fonts() {
        if (!fontPromise) {
            fontPromise = Promise.all([
                ['hearthstone-title','GBJenLei-Medium.woff2'],
                ['hearthstone-name','Belwe-Bold.ttf'],
                ['hearthstone-rules','FranklinGothic-MediumCond.woff2']
            ].map(async ([name,file]) => {
                const font = new FontFace(name, `url(/fonts/hearthstone/${file})`);
                document.fonts.add(await font.load());
            }));
        }
        return fontPromise;
    }
    // Original-style names use Belwe and individually rotated glyphs on the
    // minion/spell cubic paths documented by HearthSim/Sunwell (MIT).
    const writeFlatText = writeText;
    function pointOnNamePath(points,t) {
        const u=1-t;
        const x=u*u*u*points[0][0]+3*u*u*t*points[1][0]+3*u*t*t*points[2][0]+t*t*t*points[3][0];
        const y=u*u*u*points[0][1]+3*u*u*t*points[1][1]+3*u*t*t*points[2][1]+t*t*t*points[3][1];
        const dx=3*u*u*(points[1][0]-points[0][0])+6*u*t*(points[2][0]-points[1][0])+3*t*t*(points[3][0]-points[2][0]);
        const dy=3*u*u*(points[1][1]-points[0][1])+6*u*t*(points[2][1]-points[1][1])+3*t*t*(points[3][1]-points[2][1]);
        return {x,y,angle:Math.atan2(dy,dx)};
    }
    writeText = function(textObject,context) {
        const curve=textObject.hearthstoneCurve;
        if(!curve || curve.version!==2) return writeFlatText(textObject,context);
        // Keep the shared replacement engine available for advanced title codes.
        // Rules, costs, stats and every other text box always use that engine.
        if(/[{}]/.test(textObject.text)) return writeFlatText(textObject,context);
        const width=scaleWidth(textObject.width),height=scaleHeight(textObject.height);
        const points=curve.points.map(([x,y])=>[x*width,y*height]);
        const path=Array.from({length:1001},(_,i)=>pointOnNamePath(points,i/1000));
        let length=0;
        path.forEach((p,i)=>{if(i) length+=Math.hypot(p.x-path[i-1].x,p.y-path[i-1].y);p.distance=length;});
        const center=path[Math.round(curve.middle*1000)].distance;
        const maxWidth=Math.min(width*curve.maxWidth,2*Math.min(center,length-center));
        const letters=Array.from(new Intl.Segmenter(undefined,{granularity:'grapheme'}).segment(textObject.text),s=>s.segment);
        let size=scaleHeight(textObject.size)+parseInt(textObject.fontSize||0);
        let advances,total;
        context.save();
        do {
            context.font=`${Math.max(1,size)}px "${textObject.font}"`;
            const em=context.measureText('M').width;
            advances=letters.map(char=>char===' '?em*0.25:context.measureText(char).width+em*0.035);
            total=advances.reduce((sum,value)=>sum+value,0);
            if(total<=maxWidth || size<=1) break;
            size--;
        } while(true);
        context.translate(scaleX(textObject.x),scaleY(textObject.y));
        context.rotate((textObject.rotation||0)*Math.PI/180);
        context.textAlign='center';
        context.textBaseline='middle';
        context.lineJoin='round';
        context.lineCap='round';
        context.fillStyle=textObject.color||'white';
        context.strokeStyle=textObject.outlineColor||'black';
        context.lineWidth=size*0.11;
        let distance=center-total/2,index=0;
        letters.forEach((letter,i)=>{
            const midpoint=distance+advances[i]/2;
            while(index<path.length-1 && path[index].distance<midpoint) index++;
            const p=path[index];
            context.save();
            context.translate(p.x,p.y);
            context.rotate(p.angle);
            context.strokeText(letter,0,0);
            context.fillText(letter,0,0);
            context.restore();
            distance+=advances[i];
        });
        context.restore();
    };
    function nameOptions(k) {
        if(k==='battleground-minion') k='minion';
        if(!['minion','spell'].includes(k)) {
            const definitions={
                weapon:{ratio:370/514,x:65,y:323,bannerX:87,bannerY:468,middle:0.56,max:450,points:[[18,56],[66,56],[400,56],[456,56]]},
                hero:{ratio:353/490,x:73.5,y:316,bannerX:91,bannerY:458,middle:0.5,max:420,points:[[24,98],[170,36],[294,36],[438,96]]},
                'hero-power':{ratio:0.7,x:0,y:0,bannerX:0,bannerY:0,middle:0.54,max:440,points:[[10,37],[110,37],[350,37],[450,37]]}
            };
            if(k==='location') return {
                x:60/460,y:311/644,width:350/460,height:85/644,size:30/644,
                font:'hearthstone-name',outlineColor:'black',rotation:0,
                hearthstoneCurve:{version:2,middle:0.5,maxWidth:0.94,points:[[0,0.4],[0.3,0.85],[0.7,0.85],[1,0.45]]}
            };
            const t=definitions[k],r=t.ratio;
            return {
                x:(k==='hero-power'?15.5+105*r-20:t.x+(105-t.bannerX)*r-20)/460,
                y:(k==='hero-power'?452*r:t.y+(452-t.bannerY)*r)/644,
                width:460*r/460,height:160*r/644,size:44*r/644,
                font:'hearthstone-name',outlineColor:'black',rotation:0,
                hearthstoneCurve:{version:2,middle:t.middle,maxWidth:t.max/460,points:t.points.map(([x,y])=>[x/460,y/160])}
            };
        }
        // Map Sunwell's 460x160 name path box into the existing CardForge ribbon.
        // The asymmetric minion path is intentionally different from the spell.
        const minion=k==='minion';
        const ratio=minion?350/485:371/507;
        const points=minion?[[0,88],[98,112],[294,13],[460,80]]:[[10,78],[170,36],[294,36],[450,80]];
        return {
            x:((minion?75-96*ratio:64.5-80*ratio)+105*ratio-20+(minion?1:-2.5))/460,
            y:((minion?323-469*ratio:316-457*ratio)+452*ratio+(minion?-3.5:4))/644,
            width:ratio,height:160*ratio/644,size:(minion?44:42)*ratio/644,
            font:'hearthstone-name',outlineColor:'black',rotation:0,
            hearthstoneCurve:{version:2,middle:minion?0.55:0.49,maxWidth:450/460,
                points:points.map(([x,y])=>[x/460,y/160])}
        };
    }
    const settings = () => {
        const state={...defaults, ...(card.hearthstone || {})};
        if(state.kind && state.kind!==kind) {
            const t=profile(kind);
            state.power=!!t.left;state.toughness=!!t.right;state.dragon=!t.noRarity;
            state.mana=!!t.mana;state.tier=!!t.tier;state.type=!!t.type && t.typeDefault!==false;
        }
        if(profile(kind).noRarity) state.rarity='none';
        return state;
    };
    function showControls() {
        let panel = document.getElementById('hearthstone-controls');
        if (!panel) {
            panel = document.createElement('div');
            panel.id = 'hearthstone-controls';
            panel.className = 'readable-background margin-bottom padding';
            panel.style.fontFamily = 'gothammedium, sans-serif';
            panel.style.lineHeight = '1.5';
            panel.innerHTML = `<h3>Hearthstone components</h3>
                <div class="input-grid margin-bottom">
                    <label>Class<select id="hs-class" class="input" aria-label="Hearthstone class">${classes.map(c=>`<option value="${c}">${label(c)}</option>`).join('')}</select></label>
                    <label>Rarity<select id="hs-rarity" class="input" aria-label="Hearthstone rarity">${['none','common','rare','epic','legendary'].map(r=>`<option value="${r}">${label(r)}</option>`).join('')}</select></label>
                </div>
                <label id="hs-level-label">Tavern tier<select id="hs-level" class="input" aria-label="Tavern tier">${[1,2,3,4,5,6].map(n=>`<option value="${n}">Tier ${n}</option>`).join('')}</select></label>
                <div class="input-grid margin-bottom">${[
                    ['body','Class body'],['portrait','Art border'],['scroll','Text scroll'],['name','Name ribbon'],
                    ['mana','Mana crystal'],['power','Power symbol'],['toughness','Toughness symbol'],
                    ['type','Type indicator'],['tier','Tavern tier badge'],['dragon','Legendary dragon'],['bleed','1/8-inch black margins']
                ].map(([id,text])=>`<label><input id="hs-${id}" type="checkbox"> ${text}</label>`).join('')}</div>
                <button id="hs-build" class="input">Build / replace Hearthstone layers</button>
                <p class="input-description">Build a complete card, then edit or remove each layer below. Class and component changes apply when you build. Text and art are preserved. Hero Powers use the game's universal frame. Use the Text tab for cost, power, toughness and type (e.g. Beast). MtG codes such as {t}, {w}, {u} and {b} work in rules text.</p>`;
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
            const t=profile(kind);
            const supported={power:!!t.left,toughness:!!t.right,type:!!t.type,mana:!!t.mana,tier:!!t.tier,rarity:!t.noRarity,dragon:!t.noRarity};
            if(key in supported) {
                input.disabled=!supported[key];
                if(input.type==='checkbox' && input.disabled) input.checked=false;
                input.parentElement.style.opacity=input.disabled?'0.5':'1';
            }
            if(key==='power' || key==='toughness') {
                const text=key==='power'?t.left:t.right;
                input.parentElement.lastChild.textContent=' '+(text|| (key==='power'?'Power':'Right stat'))+' symbol';
            }
        });
        document.getElementById('hs-level-label').hidden=!profile(kind).tier;
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
        const t=profile(k);
        if(t.noRarity) state={...state,rarity:'none'};
        card.hearthstone = {...state,kind:k};
        card.margins = bleed;
        card.noCorners = true;
        document.getElementById('rounded-corners').checked = false;
        card.showsFlavorBar = false;
        drawTextBetweenFrames = false;
        // One native pixel under the frame avoids subpixel gaps at print/preview scales.
        card.artBounds={x:(t.art[0]-1)/460,y:(t.art[1]-1)/644,width:(t.art[2]+2)/460,height:(t.art[3]+2)/644};
        autoFitArt();
        card.setSymbolBounds={x:-1,y:-1,width:0.01,height:0.01};
        resetSetSymbol();
        card.watermarkBounds={x:0.5,y:0.75,width:0.45,height:0.17};
        resetWatermark();
        const box=(name,x,y,w,h,size,extra={})=>({name,text:'',x:(x-20)/460,y:y/644,width:w/460,height:h/644,size:size/644,...extra});
        const display={font:'hearthstone-title',color:'white',outlineWidth:2/644,outlineColor:'#241c18',oneLine:true,align:'center'};
        const oldPT = !card.text?.power && card.text?.pt?.text.match(/^\s*([^/]+)\/([^/]+)\s*$/);
        const textOptions = {
            title:{name:'Title',text:'',...display,...nameOptions(k)},
            mana:box('Mana cost',45,67,88,75,65,display),
            type:box('Type / tribe',153,572,204,29,21,display),
            rules:box('Rules Text',...t.rules,27,{font:'hearthstone-rules',color:t.rulesColor||'black',align:'center',justify:'center',lineSpacing:0.05}),
            power:box('Power',44,540,90,78,57,display),
            toughness:box('Toughness',366,540,80,78,57,display)
        };
        if(!t.left) delete textOptions.power;
        else textOptions.power.name=t.left;
        if(!t.right) delete textOptions.toughness;
        else {
            textOptions.toughness.name=t.right;
            if(t.rightKey!=='toughness') {textOptions[t.rightKey]=textOptions.toughness;delete textOptions.toughness;}
        }
        if(!t.type || !state.type) delete textOptions.type;
        if(k==='weapon' && textOptions.type) textOptions.type.y=560/644;
        if(t.tier) delete textOptions.mana;
        if(k==='hero-power') textOptions.mana=box('Mana cost',217,53,70,60,45,display);
        if(k==='location') textOptions.mana.y=76/644;
        loadTextOptions(textOptions);
        if(oldPT && ['minion','battleground-minion'].includes(k)) {card.text.power.text=oldPT[1].trim();card.text.toughness.text=oldPT[2].trim();}
        await loadBottomInfo({credit:{text:'{elemidinfo-artist}',x:0.12,y:0.97,width:0.76,height:0.018,size:0.013,font:'mplantin',color:'white',align:'center',oneLine:true}});
        drawFrames();
    }
    function loadPack(k, restoring=false) {
        kind=k;
        showControls();
        const t=profile(k),base=t.frame;
        availableFrames = [
            ...classes.flatMap(c=>[
                frame(label(c)+' '+t.name+' Class Body',classPart(k,c,'body')),
                frame(label(c)+' Art Border',classPart(k,c,'portrait'))
            ]),
            ...(t.mana?[frame('Mana Crystal',t.mana)]:[]),
            frame('Text Scroll',base+'-description-area'),
            frame('Name Ribbon',base+'-name'),
            ...(t.left?[frame(t.left+' Symbol',t.leftIcon)]:[]),
            ...(t.right?[frame(t.right+' Symbol',t.rightIcon)]:[]),
            ...(t.type?[frame('Type Indicator',base+'-kind')]:[]),
            ...(t.tier?[1,2,3,4,5,6].map(n=>frame('Tavern Tier '+n,'battleground-tier-'+n)):[]),
            ...(!t.noRarity?[
                frame('Legendary Dragon ('+base+'-dragon)',base+'-dragon'),
                frame('Rarity Socket',base+'-rarity-mask'),
                ...['common','rare','epic','legendary'].map(r=>frame(label(r)+' Rarity Gem',base+'-'+r))
            ]:[]),
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
            const state=readControls(),t=profile(kind),base=t.frame;
            await version(kind,state);
            // Retain other styles' layers: this action replaces only our own parts.
            const retained=card.frames.filter(f=>!f.hearthstone);
            card.frames=[];
            document.getElementById('frame-list').innerHTML='';
            const layers=[background(kind)];
            const add=(enabled,name,file)=>{if(enabled) layers.push(frame(name,file));};
            add(state.body,label(state.class)+' Class Body',classPart(kind,state.class,'body'));
            add(state.portrait,label(state.class)+' Art Border',classPart(kind,state.class,'portrait'));
            add(state.scroll,'Text Scroll',base+'-description-area');
            if(state.rarity!=='none' && !t.noRarity) {
                add(true,'Rarity Socket',base+'-rarity-mask');
                add(true,label(state.rarity)+' Rarity Gem',base+'-'+state.rarity);
            }
            add(state.name,'Name Ribbon',base+'-name');
            add(state.mana&&t.mana,'Mana Crystal',t.mana);
            add(state.power&&t.left,t.left+' Symbol',t.leftIcon);
            add(state.toughness&&t.right,t.right+' Symbol',t.rightIcon);
            add(state.type&&t.type,'Type Indicator',base+'-kind');
            add(state.dragon&&!t.noRarity&&state.rarity==='legendary','Legendary Dragon ('+base+'-dragon)',base+'-dragon');
            add(state.tier&&t.tier,'Tavern Tier '+state.level,'battleground-tier-'+state.level);
            // addFrame's loading API creates images/UI; the caller owns array order.
            card.frames=[...layers.reverse().map(f=>({...f,masks:[]})),...retained];
            for(const f of card.frames.slice().reverse()) {
                await addFrame([],f);
                // The stock loader redraws on every image event. Assemble once
                // after all parts decode, then restore normal interactive redraw.
                f.image.onload=()=>{if(!busy) drawFrames();};
            }
            await Promise.all(card.frames.map(f=>f.image.decode().catch(()=>{})));
            drawFrames();
        } finally {busy=false;button.disabled=false;}
    }
    // The shared loader rounds art inputs when reconstructing bleed offsets.
    // Save the exact pose alongside our settings, then consume it on restore so
    // repeat loads cannot walk an artwork by one pixel at half-pixel margins.
    const saveSharedCard=saveCard;
    saveCard=function(fromFile) {
        const target=fromFile?fromFile.data:card;
        if(!target?.version?.startsWith('hearthstone-') || !target.hearthstone) return saveSharedCard(fromFile);
        const previous=target.hearthstone.savedArt;
        target.hearthstone.savedArt={x:target.artX,y:target.artY,zoom:target.artZoom,rotate:target.artRotate};
        try {return saveSharedCard(fromFile);}
        finally {
            if(previous) target.hearthstone.savedArt=previous;
            else delete target.hearthstone.savedArt;
        }
    };
    async function restore() {
        await fonts();
        if(!card.version.startsWith('hearthstone-')) return;
        kind=card.hearthstone?.kind || card.version.slice('hearthstone-'.length);
        const pose=card.hearthstone?.savedArt;
        if(pose) {
            delete card.hearthstone.savedArt;
            document.querySelector('#art-x').value=pose.x*card.width;
            document.querySelector('#art-y').value=pose.y*card.height;
            document.querySelector('#art-zoom').value=pose.zoom*100;
            document.querySelector('#art-rotate').value=pose.rotate||0;
            artEdited();
        }
        // Upgrade prior default typography while retaining deliberate placement edits.
        if(card.text.title?.hearthstoneCurve?.version!==2) {
            const title=card.text.title,options=nameOptions(kind);
            if(title) {
                const oldX=78/460,oldY=(kind==='minion'?337:343)/644;
                const dx=(title.x??oldX)-oldX,dy=(title.y??oldY)-oldY;
                const position=title.font==='hearthstone-name'?{x:title.x,y:title.y,width:title.width,height:title.height}:{x:options.x+dx,y:options.y+dy};
                Object.assign(title,options,position);
            }
        }
        // Loading a save must not reset text, component positions, art or margins.
        document.querySelector('#selectFrameGroup').value='Hearthstone';
        showControls();
        const select=document.querySelector('#selectFramePack');
        select.innerHTML=packs.map(p=>`<option value="${p.value}">${p.name}</option>`).join('');
        select.value=profile(kind).pack;
        loadPack(kind,true);
        drawTextBuffer();
        drawFrames();
    }
    return {showControls,loadPack,version,build,restore,packs,types};
})();
if(card.version.startsWith('hearthstone-')) Hearthstone.restore();
