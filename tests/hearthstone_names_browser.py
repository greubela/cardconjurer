"""Check curved title placement, long-name fitting and legacy save migration.
Run with the application served at localhost:4242. Requires Playwright/Pillow.
"""
import asyncio,base64,io
from pathlib import Path
from PIL import Image,ImageDraw
from playwright.async_api import async_playwright
async def main():
 tiles=[];errors=[]
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':1600,'height':1200})
  page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto('http://localhost:4242/',wait_until='domcontentloaded')
  await page.wait_for_function("typeof card!=='undefined' && card.text")
  await page.select_option('#selectFrameGroup','Hearthstone')
  await page.wait_for_function("card.version==='hearthstone-minion'")
  assert await page.evaluate("document.fonts.check('12px hearthstone-name') && card.text.title.font==='hearthstone-name'")
  for kind,pack in [('minion','HearthstoneMinion'),('spell','HearthstoneSpell')]:
   if kind=='spell':
    await page.select_option('#selectFramePack',pack)
    await page.wait_for_function("card.version==='hearthstone-spell'")
   await page.locator('#hs-bleed').check()
   await page.click('#hs-build')
   await page.wait_for_function("!document.getElementById('hs-build').disabled")
   await page.evaluate('async()=>{await Promise.all(card.frames.map(f=>f.image.decode()));}')
   for title in ['Ragnaros','Keeper of the Grove','Alexstrasza, Guardian of the Ancient Grove']:
    await page.evaluate('''async name=>{
     card.text.title.text=name;clearTimeout(writingText);await drawText();drawFrames();
    }''',title)
    bounds=await page.evaluate('''()=>{
     const c=document.createElement('canvas');c.width=cardCanvas.width;c.height=cardCanvas.height;
     const ctx=c.getContext('2d');writeText(card.text.title,ctx);
     const data=ctx.getImageData(0,0,c.width,c.height).data;
     let left=c.width,right=0,top=c.height,bottom=0;
     for(let y=0;y<c.height;y++)for(let x=0;x<c.width;x++)if(data[(y*c.width+x)*4+3]>20) {
      left=Math.min(left,x);right=Math.max(right,x);top=Math.min(top,y);bottom=Math.max(bottom,y);
     }
     return {left,right,top,bottom,minX:scaleX(60/460),maxX:scaleX(402/460),minY:scaleY(320/644),maxY:scaleY(402/644)};
    }''')
    assert bounds['left']>=bounds['minX'] and bounds['right']<=bounds['maxX'],(title,bounds)
    assert bounds['top']>=bounds['minY'] and bounds['bottom']<=bounds['maxY'],(title,bounds)
    raw=base64.b64decode((await page.evaluate('cardCanvas.toDataURL()')).split(',')[1]);im=Image.open(io.BytesIO(raw));w,h=im.size
    im=im.crop((int(w*.13),int(h*.49),int(w*.87),int(h*.63)));im.thumbnail((800,190),Image.Resampling.LANCZOS)
    tiles.append((kind,im))
    print('PASS',kind,title,bounds,flush=True)
   # Legacy cards acquire the curve without changing edited text placement.
   assert await page.evaluate('''async()=>{
    const title=card.text.title;delete title.hearthstoneCurve;const x=title.x+0.01;title.x=x;
    await Hearthstone.restore();return title.x===x && !!title.hearthstoneCurve;
   }''')
  assert not errors,errors
  await browser.close()
 board=Image.new('RGB',(840,6*215),'#171717');d=ImageDraw.Draw(board)
 for i,(kind,im) in enumerate(tiles):
  board.paste(im,(20,i*215+20));d.text((20,i*215+195),kind,fill='white')
 output=Path('work/hearthstone-name-verification');output.mkdir(parents=True,exist_ok=True)
 board.save(output/'curved-names.jpg',quality=94)
 print('PASS: short/long names fit ribbons; legacy saves retain title placement')
if __name__=='__main__':
 asyncio.run(main())
