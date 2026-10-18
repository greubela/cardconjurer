"""Normalize CardForge's individual parts to Card Conjurer's 5:7 canvas.

Usage: python tools/build_hearthstone_assets.py /path/to/cardforge
Requires Pillow. Generated assets are checked in; no runtime dependency.
Source positions: CardForge src/components/Card/{Minion,Spell}.vue.
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


for kind in ('minion', 'spell'):
    for path in sorted((source / (kind+'s/single-class')).glob('*.png')):
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
    parts = {
        'name': (323 if kind=='minion' else 316, 0),
        'description-area': (407,0) if kind=='minion' else (-20,-1),
        'kind': (546,7) if kind=='minion' else (-21,0),
        'dragon': (21,50) if kind=='minion' else (49,68),
        'rarity-mask': (370,13) if kind=='minion' else (379,0),
    }
    for part,(y,dx) in parts.items():
        save(stage(f'materials/{kind}/{kind}-{part}.png',y,dx),kind+'-'+part)
    for rarity in ('common','rare','epic','legendary'):
        save(stage(f'materials/rarity/{rarity}-crystal.png',381 if kind=='minion' else 390,6.5 if kind=='minion' else 0),kind+'-'+rarity)
for name, path, y, dx in (
    ('mana-crystal','cost/cost-crystal',60,-160),
    ('power-symbol','common/attack',505,-170),
    ('toughness-symbol','common/vitality',511,156),
):
    save(stage('materials/'+path+'.png',y,dx),name)
print('Generated',len(list(target.glob('*.png'))),'assets')
