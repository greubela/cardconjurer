"""End-to-end Hearthstone checks in a real Chromium browser.

Start the application at localhost:4242, then run:
  python tests/hearthstone_browser.py --art /absolute/path/to/test-art.png
Requires Playwright (Python), Pillow and Chromium. Art is optional; a vivid
checkerboard is used otherwise to reveal leaking art outside irregular frames.
Artifacts go to work/hearthstone-verification unless --output is supplied.
"""
import argparse
import asyncio
import base64
import io
import json
from pathlib import Path
from PIL import Image, ImageDraw
from playwright.async_api import async_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://localhost:4242/')
parser.add_argument('--output', default='work/hearthstone-verification')
parser.add_argument('--art', type=Path)
parser.add_argument('--quick', action='store_true', help='Recheck Neutral, Druid and Mage plus every behavior check')
args = parser.parse_args()
out = Path(args.output)
out.mkdir(parents=True, exist_ok=True)
classes = ['neutral','deathknight','demonhunter','druid','hunter','mage','paladin','priest','rogue','shaman','warlock','warrior']


def artwork():
    if args.art:
        return 'data:image/png;base64,'+base64.b64encode(args.art.read_bytes()).decode()
    im=Image.new('RGB',(600,800),'magenta')
    d=ImageDraw.Draw(im)
    for y in range(0,800,80):
        for x in range(0,600,80):
            if (x+y)//80 % 2: d.rectangle((x,y,x+79,y+79),fill='cyan')
    buf=io.BytesIO();im.save(buf,format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()


async def ready(page):
    await page.goto(args.url,wait_until='domcontentloaded')
    await page.wait_for_function("typeof card !== 'undefined' && card.text && typeof loadCard === 'function'")


async def settle(page):
    await page.evaluate('''async () => {
        await Promise.all(card.frames.map(f=>f.image?.decode().catch(()=>{})));
        await document.fonts.ready;
        clearTimeout(writingText);await drawText();drawFrames();
    }''')


async def build(page, cls='neutral', rarity='none', bleed=False):
    await page.select_option('#hs-class',cls)
    await page.select_option('#hs-rarity',rarity)
    await page.locator('#hs-bleed').set_checked(bleed)
    await page.click('#hs-build')
    await page.wait_for_function("!document.getElementById('hs-build').disabled")
    await settle(page)


async def export(page,name):
    data=await page.evaluate('cardCanvas.toDataURL()')
    raw=base64.b64decode(data.split(',')[1])
    (out/(name+'.png')).write_bytes(raw)
    return Image.open(io.BytesIO(raw)).convert('RGBA')


def black_edges(im, margin_x=.05, margin_y=1/28):
    # Scan every pixel in all four bleed strips, plus irregular trim corners.
    w,h=im.size
    mx=round(2010*margin_x);my=round(2814*margin_y)
    for crop in [(0,0,w,my-1),(0,h-my+1,w,h),(0,0,mx-1,h),(w-mx+1,0,w,h)]:
        extrema=im.crop(crop).getextrema()
        assert extrema == ((0,0),(0,0),(0,0),(255,255)), (crop,extrema)
    for x,y in [(mx+2,my+2),(w-mx-3,my+2),(mx+2,h-my-3),(w-mx-3,h-my-3)]:
        assert im.getpixel((x,y)) == (0,0,0,255)


async def main():
    errors=[]
    failed=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        context=await browser.new_context(viewport={'width':1900,'height':1450},device_scale_factor=1,accept_downloads=True)
        page=await context.new_page()
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('response',lambda r:failed.append((r.status,r.url)) if r.status>=400 and 'hearthstone' in r.url.lower() else None)
        await ready(page)
        await page.select_option('#selectFrameGroup','Hearthstone')
        await page.wait_for_function("card.version === 'hearthstone-minion'")
        await build(page)
        assert await page.evaluate('card.text.title.hearthstoneCurve.rise>0')
        await page.evaluate(r'''async source => {
            uploadArt(source,'autoFit');await art.decode();autoFitArt();
            card.text.title.text='Keeper of the Grove';
            card.text.mana.text='4';card.text.type.text='Beast';
            card.text.power.text='2';card.text.toughness.text='4';
            card.text.rules.text='{bold}Choose One —{/bold}\nDeal 2 damage; or\n{t}: Add {g}{g}.';
            document.querySelector('#info-artist').value='Demonstration artwork';
            await bottomInfoEdited();
        }''',artwork())
        # Observe the actual canvas image calls while rendering MtG replacements.
        symbols=await page.evaluate('''async () => {
            const original=CanvasRenderingContext2D.prototype.drawImage;
            const seen=[];
            CanvasRenderingContext2D.prototype.drawImage=function(im,...rest) {
                if(im.src?.includes('/manaSymbols/'))seen.push(im.src);
                return original.call(this,im,...rest);
            };
            try {clearTimeout(writingText);await drawText();} finally {CanvasRenderingContext2D.prototype.drawImage=original;}
            return seen;
        }''')
        assert any(s.endswith('/t.svg') for s in symbols),symbols
        assert sum(s.endswith('/g.svg') for s in symbols)>=2,symbols
        await export(page,'neutral-minion')
        # Every class in both packs must assemble and load its real images.
        grids={}
        for kind,pack in [('minion','HearthstoneMinion'),('spell','HearthstoneSpell')]:
            if kind=='spell':
                await page.select_option('#selectFramePack',pack)
                await page.wait_for_function("card.version==='hearthstone-spell'")
                await page.evaluate("card.text.title.text='Grovefire';card.text.type.text='Nature';card.text.rules.text='Deal 3 damage.\\n{t}: Add {r}{g}.'")
            tiles=[]
            for cls in (['neutral','druid','mage'] if args.quick else classes):
                await build(page,cls,'legendary',True)
                assert await page.evaluate('card.frames.every(f=>f.image.complete&&f.image.naturalWidth>0)')
                assert await page.evaluate("card.frames.some(f=>f.name.includes('Dragon'))")
                assert await page.evaluate('cardCanvas.width===2211 && cardCanvas.height===3015')
                im=await export(page,cls+'-'+kind)
                black_edges(im)
                im.thumbnail((280,382),Image.Resampling.LANCZOS)
                tiles.append((cls,im))
            grid=Image.new('RGB',(4*300,3*420),'#171717')
            d=ImageDraw.Draw(grid)
            for i,(cls,im) in enumerate(tiles):
                x=i%4*300;y=i//4*420
                grid.paste(im,(x+10,y),im);d.text((x+12,y+388),cls,fill='white')
            grid.save(out/(kind+'-classes.jpg'),quality=92)
            grids[kind]=grid
            print('Verified',len(tiles),kind,'classes and full black bleed',flush=True)
        # Disabling components excludes precisely those layers, preserving rules.
        for key in ['mana','scroll','type','dragon']:
            await page.locator('#hs-'+key).uncheck()
        await build(page,'mage','legendary',True)
        names=await page.evaluate('card.frames.map(f=>f.name)')
        assert not any(any(s in n for s in ['Mana Crystal','Text Scroll','Type Indicator','Dragon']) for n in names),names
        for key in ['mana','scroll','type','dragon']:
            await page.locator('#hs-'+key).check()
        await build(page,'mage','legendary',True)
        # Exercise the existing text and frame editors through real UI inputs.
        await page.locator('#creator-menu-tabs h3').filter(has_text='Text').click()
        await page.locator('#text-options h4').filter(has_text='Title').click()
        await page.locator('#text-editor').fill('Saved Grovefire')
        assert await page.evaluate("card.text.title.text==='Saved Grovefire'")
        await page.locator('#creator-menu-tabs h3').filter(has_text='Frame').click()
        await page.locator('#frame-list .frame-element').first.click()
        await page.locator('#frame-editor-x').fill('8')
        await page.locator('#frame-editor-x').dispatch_event('change')
        await page.locator('#frame-editor-opacity').fill('93')
        await page.locator('#frame-editor-opacity').dispatch_event('change')
        await page.locator('.frame-element-editor-close').click()
        assert await page.evaluate('card.frames[0].opacity==93 && card.frames[0].bounds.x===8/card.width')
        # Manual frame layer editing: bounds and opacity survive save/reload.
        await page.evaluate('''() => {
            card.text.title.x+=0.003;
            const data=JSON.parse(JSON.stringify(card));
            data.frames.forEach(f=>{delete f.image;f.masks.forEach(m=>delete m.image)});
            saveCard({key:'Hearthstone Browser Test',data});
        }''')
        saved=await page.evaluate('JSON.parse(localStorage.getItem("Hearthstone Browser Test"))')
        # A fresh page verifies font and onload initialization from an MtG session.
        fresh=await context.new_page();fresh.on('pageerror',lambda e:errors.append(str(e)))
        await ready(fresh)
        await fresh.evaluate("loadCard('Hearthstone Browser Test')")
        await fresh.wait_for_function("typeof Hearthstone!=='undefined' && document.querySelector('#hs-class')?.value==='mage'")
        await settle(fresh)
        restored=await fresh.evaluate('JSON.parse(JSON.stringify(card))')
        for key in ['text','hearthstone','artBounds','artX','artY','artZoom','marginX','marginY']:
            assert restored[key]==saved[key],key
        for before,after in zip(saved['frames'],restored['frames']):
            for key in ['name','bounds','opacity','src']:
                assert before.get(key)==after.get(key),(key,before,after)
        await export(fresh,'saved-legendary-spell')
        # Existing generic margin workflow retains Hearthstone geometry and black.
        await fresh.select_option('#selectFrameGroup','Margin')
        await fresh.wait_for_function('card.marginX===0.044')
        await settle(fresh)
        assert await fresh.evaluate("card.version==='hearthstone-spell'")
        black_edges(await export(fresh,'generic-margin-spell'), .044, 1/35)
        # Return to the regular MtG pack and exercise its existing text layout.
        await fresh.select_option('#selectFrameGroup','Standard-3')
        await fresh.wait_for_function("card.version==='m15Regular'")
        assert await fresh.locator('#hearthstone-controls').is_hidden()
        assert await fresh.evaluate("card.text.pt.name==='Power/Toughness'")
        # Reopen the saved card for screenshots and a real PNG download.
        await fresh.evaluate("loadCard('Hearthstone Browser Test')")
        await settle(fresh)
        await fresh.evaluate("card.frames[0].bounds={x:0,y:0,width:1,height:1};card.frames[0].opacity=100;drawFrames()")
        await export(fresh,'legendary-spell')
        async with fresh.expect_download() as download:
            await fresh.evaluate('downloadCard()')
        await (await download.value).save_as(out/'downloaded-card.png')
        assert Image.open(out/'downloaded-card.png').size==(2211,3015)
        await fresh.screenshot(path=str(out/'editor-spell.png'))
        await fresh.select_option('#selectFramePack','HearthstoneMinion')
        await fresh.wait_for_function("card.version==='hearthstone-minion'")
        await build(fresh,'druid','legendary',True)
        await fresh.evaluate("card.text.title.text='Keeper of the Grove';card.text.type.text='Beast';card.text.power.text='2';card.text.toughness.text='4';card.text.rules.text='{bold}Choose One —{/bold}\\nDeal 2 damage; or\\n{t}: Add {g}{g}.'")
        await settle(fresh)
        await fresh.screenshot(path=str(out/'editor-minion.png'))
        black_edges(await export(fresh,'legendary-minion'))
        # Mobile controls must fit the viewport and remain usable.
        await fresh.set_viewport_size({'width':390,'height':844})
        await fresh.locator('#hs-class').scroll_into_view_if_needed()
        await fresh.select_option('#hs-class','hunter')
        assert await fresh.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'Mobile overflow'
        await fresh.screenshot(path=str(out/'mobile-controls.png'))
        assert not errors, errors
        assert not failed, failed
        (out/'results.json').write_text(json.dumps({'classes':6 if args.quick else 24,'symbols':['t','g'],'bleed':'1/8 inch; all four strips and trim corners opaque black','save_reload':'text, art, positions, layer opacity, settings preserved','png_download':[2211,3015],'mobile_width':390,'page_errors':errors,'failed_extension_requests':failed},indent=2))
        await browser.close()
    print('PASS: browser visuals,',6 if args.quick else 24,'class variants, components, MtG symbols, bleed, save/reload, download, mobile and regular MtG switch',flush=True)

if __name__ == '__main__':
    asyncio.run(main())
