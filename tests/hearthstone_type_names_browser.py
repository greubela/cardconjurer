"""Verify long title glyphs remain ordered on every Hearthstone name path.
Run with the application served at localhost:4242; requires Python Playwright.
"""
import asyncio
from playwright.async_api import async_playwright
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);page=await browser.new_page()
  await page.goto('http://localhost:4242/',wait_until='domcontentloaded');await page.wait_for_function("typeof card!=='undefined' && card.text")
  await page.select_option('#selectFrameGroup','Hearthstone');await page.wait_for_function("card.version==='hearthstone-minion'")
  kinds=await page.evaluate('Object.keys(Hearthstone.types)')
  for kind in kinds:
   await page.evaluate('k=>Hearthstone.loadPack(k)',kind);await page.wait_for_function("k=>card.version==='hearthstone-'+k",arg=kind)
   assets=await page.evaluate('''async()=>{await Promise.all(availableFrames.map(async f=>{const im=new Image();im.src=f.src;await im.decode()}));return availableFrames.length}''')
   result=await page.evaluate('''()=>{
    const c=document.createElement('canvas');c.width=card.width;c.height=card.height;const ctx=c.getContext('2d'),original=ctx.fillText,positions=[];
    ctx.fillText=function(char,...rest){positions.push({char,x:this.getTransform().e,y:this.getTransform().f});return original.call(this,char,...rest)};
    writeText({...card.text.title,text:'Alexstrasza, Keeper of the Ancient Grove and Guardian of the Emerald Dream'},ctx);
    return positions;
   }''')
   assert all(result[i]['x']>result[i-1]['x'] for i in range(1,len(result))),(kind,result)
   print('PASS',kind,'long title glyphs follow path;',assets,'component images decode',flush=True)
  await browser.close()
if __name__=='__main__':asyncio.run(main())
