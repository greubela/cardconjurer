"""Browser verification of every exposed Hearthstone type and class.

Serve the repository at localhost:4242, then run this file. Requires Python
Playwright, Pillow and /usr/bin/chromium. Class coverage uses the application's
half-resolution canvas; each type is also verified at full print resolution,
including fresh-page save/reload, real PNG download and exact black bleed.
"""
import argparse
import asyncio
import base64
import io
import json
from pathlib import Path
from PIL import Image, ImageDraw
from playwright.async_api import async_playwright

parser=argparse.ArgumentParser()
parser.add_argument('--url',default='http://localhost:4242/')
parser.add_argument('--output',default='work/hearthstone-matrix')
parser.add_argument('--quick',action='store_true')
parser.add_argument('--kinds',nargs='*')
args=parser.parse_args()
out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
classes=['neutral','deathknight','demonhunter','druid','hunter','mage','paladin','priest','rogue','shaman','warlock','warrior']


def art_source():
    image=Image.new('RGB',(240,400),'magenta');d=ImageDraw.Draw(image)
    for y in range(0,400,40):
        for x in range(0,240,40):
            if (x+y)//40%2:d.rectangle((x,y,x+39,y+39),fill='cyan')
    data=io.BytesIO();image.save(data,format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(data.getvalue()).decode()


def verify_pixels(image,width,height):
    assert image.size==(round(width*1.1),round(height*15/14)),image.size
    if image.getchannel('A').getextrema()!=(255,255):image.save(out/'failed-alpha.png')
    assert image.getchannel('A').getextrema()==(255,255),('Unfilled pixels in card or art aperture',image.getchannel('A').getextrema())
    w,h=image.size;mx=round(width*.05);my=round(height/28)
    for rectangle in [(0,0,w,my-1),(0,h-my+1,w,h),(0,0,mx-1,h),(w-mx+1,0,w,h)]:
        assert image.crop(rectangle).getextrema()==((0,0),(0,0),(0,0),(255,255)),rectangle
    for x,y in [(mx+2,my+2),(w-mx-3,my+2),(mx+2,h-my-3),(w-mx-3,h-my-3)]:
        assert image.getpixel((x,y))==(0,0,0,255),'Unfilled irregular trim corner'


async def ready(page):
    await page.goto(args.url,wait_until='domcontentloaded')
    await page.wait_for_function("typeof card!=='undefined' && card.text")


async def settle(page):
    await page.evaluate('''async()=>{
        await Promise.all(card.frames.map(f=>f.image.decode()));await document.fonts.ready;
        clearTimeout(writingText);await drawText();drawFrames();
    }''')


async def card_image(page):
    data=await page.evaluate('cardCanvas.toDataURL()')
    return Image.open(io.BytesIO(base64.b64decode(data.split(',')[1]))).convert('RGBA')


async def build(page,t,cls,tier=1):
    await page.select_option('#hs-class',cls)
    if not t.get('noRarity'):await page.select_option('#hs-rarity','legendary')
    for key in ['body','portrait','scroll','name','mana','power','toughness','type','dragon','tier','bleed']:
        checkbox=page.locator('#hs-'+key)
        if await checkbox.is_enabled():await checkbox.check()
    if t.get('tier'):await page.select_option('#hs-level',str(tier))
    await page.click('#hs-build')
    await page.wait_for_function("!document.getElementById('hs-build').disabled")
    await page.evaluate(r'''kind=>{
        const names={minion:'Keeper of the Grove',spell:'Fireball',weapon:'Frostmourne',hero:'Frost Lich Jaina',location:'Nightcloak Sanctum','hero-power':'Fireblast','battleground-minion':'Tavern Guardian'};
        Object.entries(card.text).forEach(([key,f])=>{
            f.text=key==='title'?names[kind]:key==='rules'?'{t}: Add {u}.\nDraw a card.':key==='type'?'Beast':key==='armor'?'5':key==='durability'?'3':key==='mana'?'4':key==='power'?'2':'4';
        });
        document.querySelector('#info-artist').value='Generated test pattern';bottomInfoEdited();
    }''',t['kind'])
    await settle(page)


async def snapshot(page):
    return await page.evaluate('''()=>({
        text:card.text,hearthstone:card.hearthstone,art:[card.artSource,card.artX,card.artY,card.artZoom],
        dimensions:[card.width,card.height,card.marginX,card.marginY],
        frames:card.frames.map(({src,name,bounds,opacity,masks})=>({src,name,bounds,opacity,masks:masks.map(({src,name})=>({src,name}))}))
    })''')


async def main():
    errors=[];failed=[];records=[];representatives=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        context=await browser.new_context(viewport={'width':1900,'height':1450},accept_downloads=True)
        page=await context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('response',lambda r:failed.append([r.status,r.url]) if r.status>=400 and 'hearthstone' in r.url.lower() else None)
        await ready(page)
        await page.select_option('#selectFrameGroup','Hearthstone')
        await page.wait_for_function("card.version==='hearthstone-minion'")
        definitions=await page.evaluate('Object.entries(Hearthstone.types).map(([kind,t])=>({kind,...t}))')
        assert len(definitions)==7
        if args.kinds:definitions=[t for t in definitions if t['kind'] in args.kinds]
        await page.evaluate('''async source=>{uploadArt(source,'autoFit');await art.decode();autoFitArt();}''',art_source())
        for t in definitions:
            k=t['kind'];tiles=[]
            await page.evaluate('getStandardWidth=()=>1005;getStandardHeight=()=>1407')
            await page.select_option('#selectFramePack',t['pack'])
            await page.wait_for_function("k=>card.version==='hearthstone-'+k",arg=k)
            for i,cls in enumerate(classes if not args.quick else ['neutral','deathknight','demonhunter','mage']):
                await build(page,t,cls,i%6+1)
                state=await snapshot(page)
                assert state['hearthstone']['class']==cls and state['hearthstone']['kind']==k
                assert await page.evaluate('card.frames.every(f=>f.image.naturalWidth>0)')
                if not t.get('universal'):
                    assert any('/'+cls+'-'+t['frame']+'-body.png' in f['src'] for f in state['frames'])
                expected={'title','rules'}
                if t.get('mana'):expected.add('mana')
                if t.get('left'):expected.add('power')
                if t.get('right'):expected.add(t['rightKey'])
                if t.get('type'):expected.add('type')
                assert set(state['text'])==expected,(k,set(state['text']),expected)
                if t.get('tier'):
                    assert any(f['name']=='Tavern Tier '+str(i%6+1) for f in state['frames'])
                    assert 'mana' not in state['text']
                if t.get('noRarity'):
                    assert not any('Dragon' in f['name'] or 'Rarity' in f['name'] for f in state['frames'])
                image=await card_image(page);verify_pixels(image,1005,1407)
                image.thumbnail((235,325),Image.Resampling.LANCZOS);tiles.append((cls,image))
                records.append({'kind':k,'class':cls,'passed':True})
            grid=Image.new('RGB',(1000,3*365),'#171717');d=ImageDraw.Draw(grid)
            for i,(cls,image) in enumerate(tiles):
                x=i%4*250;y=i//4*365;grid.paste(image,(x,y),image);d.text((x+10,y+330),cls,fill='white')
            grid.save(out/(k+'-classes.jpg'),quality=92)
            print('PASS',k,len(tiles),'classes, applicable components and opaque black bleed',flush=True)
            # Full-resolution print output, symbols and independent component removal.
            await page.evaluate('getStandardWidth=()=>2010;getStandardHeight=()=>2814')
            await build(page,t,'mage',6)
            image=await card_image(page);verify_pixels(image,2010,2814);image.save(out/(k+'-print.png'))
            representative=image.copy();representative.thumbnail((340,470));representatives.append((t['name'],representative))
            symbols=await page.evaluate('''async()=>{
                const seen=[],original=CanvasRenderingContext2D.prototype.drawImage;
                CanvasRenderingContext2D.prototype.drawImage=function(im,...a){if(im.src?.includes('/manaSymbols/'))seen.push(im.src);return original.call(this,im,...a)};
                try{await drawText()}finally{CanvasRenderingContext2D.prototype.drawImage=original}return seen;
            }''')
            assert any(s.endswith('/t.svg') for s in symbols) and any(s.endswith('/u.svg') for s in symbols),k
            before=await snapshot(page)
            await page.evaluate('''key=>{
                const data=JSON.parse(JSON.stringify(card));data.frames.forEach(f=>{delete f.image;f.masks.forEach(m=>delete m.image)});
                saveCard({key,data});
            }''','Matrix '+k)
            fresh=await context.new_page();fresh.on('pageerror',lambda e:errors.append(str(e)))
            await ready(fresh);await fresh.evaluate('key=>loadCard(key)','Matrix '+k)
            await fresh.wait_for_function("k=>typeof Hearthstone!=='undefined' && document.querySelector('#selectFramePack').value===Hearthstone.types[k].pack",arg=k)
            await settle(fresh)
            after=await snapshot(fresh)
            if after!=before:(out/'failed-state.json').write_text(json.dumps({'kind':k,'before':before,'after':after},indent=2))
            assert after==before,'Fresh-page restore changed '+k
            await fresh.screenshot(path=str(out/(k+'-editor.png')))
            async with fresh.expect_download() as download:await fresh.evaluate('downloadCard()')
            downloaded=await download.value;await downloaded.save_as(out/(k+'-download.png'))
            assert Image.open(out/(k+'-download.png')).size==(2211,3015)
            await fresh.close()
            for key in ['body','portrait','scroll','name','mana','power','toughness','type','dragon','tier']:
                checkbox=page.locator('#hs-'+key)
                if await checkbox.is_enabled():await checkbox.uncheck()
            if not t.get('noRarity'):await page.select_option('#hs-rarity','none')
            await page.click('#hs-build');await page.wait_for_function("!document.getElementById('hs-build').disabled")
            assert await page.evaluate('card.frames.length===1'),k+' kept a disabled component'
            # Restore the normal layout before changing types.
            await build(page,t,'mage')
            print('PASS',k,'print resolution, MtG symbols, fresh save/reload, download and component removal',flush=True)
        # Mobile controls on every type, including the BG tier selector.
        await page.set_viewport_size({'width':390,'height':844})
        for t in definitions:
            await page.select_option('#selectFramePack',t['pack'])
            await page.wait_for_function("k=>card.version==='hearthstone-'+k",arg=t['kind'])
            await page.locator('#hs-class').scroll_into_view_if_needed()
            assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth'),t['kind']
        await page.screenshot(path=str(out/'mobile-controls.png'))
        assert not errors,errors
        assert not failed,failed
        summary=Image.new('RGB',(4*360,2*515),'#171717');d=ImageDraw.Draw(summary)
        for i,(name,image) in enumerate(representatives):
            x=i%4*360;y=i//4*515;summary.paste(image,(x,y),image);d.text((x+10,y+480),name,fill='white')
        summary.save(out/'all-types.jpg',quality=94)
        result={'types':[t['kind'] for t in definitions],'classes':classes if not args.quick else ['neutral','deathknight','demonhunter','mage'],'combinations':len(records),'cases':records,'full_resolution_types':len(definitions),'checks':['all class assets load','correct stat and text fields','no leaked alpha','all four black bleed strips and trim corners','MtG tap and mana symbols','fresh-page save/reload for every type','PNG download for every type','independent component removal','mobile controls for every type'],'page_errors':errors,'failed_extension_requests':failed}
        (out/'results.json').write_text(json.dumps(result,indent=2))
        await browser.close()
    print('PASS:',len(records),'type/class combinations;',len(definitions),'full-resolution save/export checks',flush=True)

if __name__=='__main__':asyncio.run(main())
