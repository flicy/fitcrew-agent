"""Generate original native tab glyphs; requires Pillow. No downloaded assets."""
from pathlib import Path
from PIL import Image, ImageDraw
root = Path(__file__).resolve().parents[2] / 'apps/wechat-mini/assets/tabs'
for selected, color in [(False, '#756A81'), (True, '#6544A3')]:
    for name in ['today', 'journey', 'experiments', 'log', 'profile']:
        image = Image.new('RGBA', (192, 192))
        d = ImageDraw.Draw(image)
        def line(points): d.line([(x*8,y*8) for x,y in points], fill=color, width=13, joint='curve')
        def oval(box): d.ellipse(tuple(n*8 for n in box), outline=color, width=13)
        if name == 'today':
            oval((7,7,17,17))
            for a,b in [((12,2),(12,4)),((12,20),(12,22)),((2,12),(4,12)),((20,12),(22,12)),((5,5),(6,6)),((18,18),(19,19)),((5,19),(6,18)),((18,6),(19,5))]: line([a,b])
        elif name == 'journey':
            line([(5,20),(5,14),(12,14),(12,8),(19,8),(19,3)])
            oval((2,17,8,23)); oval((16,1,22,7))
        elif name == 'experiments':
            line([(8,3),(16,3)]); line([(10,3),(10,10),(4,19),(5,21),(19,21),(20,19),(14,10),(14,3)]); line([(8,15),(16,15)])
        elif name == 'log':
            d.rounded_rectangle((24,24,168,168),radius=36,outline=color,width=13)
            line([(12,7),(12,17)]);line([(7,12),(17,12)])
        else:
            oval((8,3,16,11)); d.arc((32,112,160,208),180,360,fill=color,width=13);line([(4,20),(20,20)])
        image.resize((72,72),Image.Resampling.LANCZOS).save(root / (name + ('-active' if selected else '') + '.png'))
