"""Normalize CardForge's individual parts to Card Conjurer's 5:7 canvas.

Usage: python tools/build_hearthstone_assets.py /path/to/cardforge /path/to/sunwell
Requires Pillow. Generated assets are checked in; no runtime dependency.
Source positions: CardForge src/components/Card/*.vue; Sunwell HeroPowerCard.ts.
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops

source = Path(sys.argv[1]) / 'src/assets'
target = Path(__file__).resolve().parents[1] / 'img/frames/hearthstone'
target.mkdir(parents=True, exist_ok=True)
CROP = (20, 0, 480, 644)


def stage(path, y=0, dx=0):
    im = Image.open(source / path).convert('RGBA')
    canvas = Image.new('RGBA', (500, 700))
    canvas.paste(im, (round((500-im.width)/2+dx), y))
    return canvas


def save(im, name, crop=True):
    im = im.crop(CROP) if crop else im
    im.save(target / (name+'.png'), optimize=True)
    im.thumbnail((160, 224), Image.Resampling.LANCZOS)
    im.save(target / (name+'Thumb.png'), optimize=True)


for kind in ('minion', 'spell', 'weapon', 'hero', 'location'):
    for path in sorted((source / (('heroes' if kind=='hero' else kind+'s')+'/single-class')).glob('*.png')):
        base = stage(path.relative_to(source), -20)
        # Separate the portrait surround from the class body; recombining these
        # complementary masks reproduces the original frame exactly.
        surround = Image.new('L', base.size)
        d = ImageDraw.Draw(surround)
        if kind == 'minion':
            d.ellipse((118, 45, 384, 405), fill=255)
        else:
            d.rectangle((0, 0, 500, 395), fill=255)
        portrait = base.copy()
        portrait.putalpha(ImageChops.multiply(base.getchannel('A'), surround))
        body = base.copy()
        body.putalpha(ImageChops.multiply(base.getchannel('A'), ImageChops.invert(surround)))
        # Remove the baked-in parchment: the clean text scroll is its own part.
        paper = Image.new('L', base.size, 255)
        ImageDraw.Draw(paper).polygon([(100,420),(400,420),(400,585),(100,585)], fill=0)
        body.putalpha(ImageChops.multiply(body.getchannel('A'), paper))
        save(portrait, path.stem+'-portrait')
        save(body, path.stem+'-body')
        if path.stem.startswith('neutral'):
            # Keep only the enclosed transparent art aperture. Everywhere else,
            # including irregular outer corners and the complete bleed, is black.
            alpha = base.getchannel('A').point(lambda p: 255 if p < 8 else 0)
            ImageDraw.floodfill(alpha, (250,200), 128)
            hole = alpha.point(lambda p: 255 if p == 128 else 0).crop(CROP)
            background = Image.new('RGBA', (506,690), (0,0,0,255))
            background.paste(Image.new('RGBA', hole.size), (23,23), hole)
            save(background, kind+'-black-surround', crop=False)
    layouts = {
        'minion': {'name':(323,0),'description-area':(407,0),'kind':(546,7),'dragon':(21,50),'rarity-mask':(370,13),'gem':(381,6.5)},
        'spell': {'name':(316,0),'description-area':(-20,-1),'kind':(-21,0),'dragon':(49,50),'rarity-mask':(379,0),'gem':(390,0)},
        'weapon': {'name':(323,0),'description-area':(407,0),'kind':(556,-1),'dragon':(32,51),'rarity-mask':(364,1),'gem':(384,1)},
        'hero': {'name':(316,0),'description-area':(382,0),'dragon':(12,45),'rarity-mask':(369,0),'gem':(381,-2)},
        'location': {'name':(325,7),'description-area':(395,0),'dragon':(8,65),'rarity-mask':(391,0),'gem':(393,-1)},
    }
    parts=layouts[kind]
    for part,(y,dx) in parts.items():
        if part!='gem':
            save(stage(f'materials/{kind}/{kind}-{part}.png',y,dx),kind+'-'+part)
    for rarity in ('common','rare','epic','legendary'):
        y,dx=parts['gem']
        save(stage(f'materials/rarity/{rarity}-crystal.png',y,dx),kind+'-'+rarity)
for name, path, y, dx in (
    ('mana-crystal','cost/cost-crystal',60,-160),
    ('power-symbol','common/attack',505,-170),
    ('toughness-symbol','common/vitality',511,156),
    ('armor-symbol','common/armor',528,156),
    ('weapon-power-symbol','weapon/weapon-attack',530,-160),
    ('durability-symbol','weapon/weapon-durability',525,158),
    ('location-durability-symbol','weapon/weapon-durability',525,163),
    ('location-mana-crystal','cost/cost-crystal',69,-160),
):
    save(stage('materials/'+path+'.png',y,dx),name)
for tier in range(1,7):
    save(stage(f'materials/battlegrounds/level-{tier}.png',60,-148),'battleground-tier-'+str(tier))

# Hero Powers have a universal frame rather than a class-colored card body.
# Sunwell's 668px scene is mapped into this same native 500px stage.
sunwell=Path(sys.argv[2]) if len(sys.argv)>2 else None
if sunwell is None:
    raise SystemExit('Pass the Sunwell checkout as the second argument to generate Hero Powers.')
im=Image.open(sunwell/'assets/hero-power-player.png').convert('RGBA')
im=im.resize((395,589),Image.Resampling.LANCZOS)
base=Image.new('RGBA',(500,700));base.paste(im,(55,45))
regions={
    'mana-crystal':(212,45,295,132),
    'portrait':(110,65,405,310),
    'name':(82,310,425,387),
    'description-area':(95,402,408,605),
}
body=base.copy()
claimed=Image.new('L',base.size)
for part,rectangle in regions.items():
    mask=Image.new('L',base.size);ImageDraw.Draw(mask).rectangle(rectangle,fill=255)
    mask=ImageChops.multiply(mask,ImageChops.invert(claimed))
    claimed=ImageChops.lighter(claimed,mask)
    layer=base.copy();layer.putalpha(ImageChops.multiply(base.getchannel('A'),mask));save(layer,'hero-power-'+part)
    body.putalpha(ImageChops.multiply(body.getchannel('A'),ImageChops.invert(mask)))
save(body,'hero-power-body')
alpha=base.getchannel('A').point(lambda p:255 if p<8 else 0)
ImageDraw.floodfill(alpha,(250,200),128)
hole=alpha.point(lambda p:255 if p==128 else 0).crop(CROP)
background=Image.new('RGBA',(506,690),(0,0,0,255))
background.paste(Image.new('RGBA',hole.size),(23,23),hole)
save(background,'hero-power-black-surround',crop=False)
print('Generated' ,len(list(target.glob('*.png'))),'assets')
