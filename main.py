import os
from nicegui import ui, app
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io
import cv2, numpy as np, mediapipe as mp
import base64, qrcode, socket, tempfile, shutil, time, asyncio

B=Path(__file__).parent
BG,OUT=B/'backgrounds',B/'output'
FRAME=B/'frame/frame1.png'
FONT=B/'font/font.ttf'FONT=Path('/usr/share/fonts/truetype/nanum/NanumGothic.ttf')
MODEL=B/'model/selfie_segmenter.tflite'
OUT.mkdir(exist_ok=True)

for u,p in [('/bg',BG),('/out',OUT),('/bgm',B/'bgm')]:
    app.add_static_files(u,str(p))

TMP=Path(tempfile.gettempdir())/'ys.tflite'
shutil.copyfile(MODEL,TMP)

N=['황포돛배와 영산강 노을','느러지 한반도 물돌이','푸른 영산강 풍경','영산강 빛의 산책로',
   '영산강 코스모스 정원','황포돛배와 영산강','영산강 양귀비 꽃밭','2026 나주영산강축제']
sel=1

SEGMENTER = None

def get_segmenter():
    ...


def read(p):
    return cv2.imdecode(np.fromfile(str(p),np.uint8),1)


def crop(x):
    h,w=x.shape[:2]
    if w/h>1.5:
        n=int(h*1.5)
        return x[:,(w-n)//2:(w+n)//2]
    n=int(w/1.5)
    return x[(h-n)//2:(h+n)//2]


def cut(p,n):
    p=cv2.resize(crop(p),(1200,800))
    bg=cv2.resize(crop(read(BG/f'bg_{n}.png')),(1200,800))

    x=mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=np.ascontiguousarray(cv2.cvtColor(p,cv2.COLOR_BGR2RGB))
    )

    o=mp.tasks.vision.ImageSegmenterOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(TMP)),
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        output_category_mask=True
    )

    with mp.tasks.vision.ImageSegmenter.create_from_options(o) as s:
        r=s.segment(x)

    m=cv2.resize(
        np.squeeze(r.category_mask.numpy_view().copy()),
        (1200,800),
        interpolation=cv2.INTER_NEAREST
    )

    m=cv2.GaussianBlur((m==0).astype(float),(0,0),.7)[:,:,None]
    return np.uint8(np.clip(p*m+bg*(1-m),0,255))


def frame(file,msg):
    f=Image.open(FRAME).convert('RGB')
    W,H=f.size
    p=Image.open(OUT/file).convert('RGB')

    x1,x2=int(W*.065),int(W*.935)
    y1,y2=int(H*.205),int(H*.665)
    w,h=x2-x1,y2-y1

    r=max(w/p.width,h/p.height)
    p=p.resize((int(p.width*r),int(p.height*r)))

    l,t=(p.width-w)//2,(p.height-h)//2
    f.paste(p.crop((l,t,l+w,t+h)),(x1,y1))

    d=ImageDraw.Draw(f)
    lines=[x.strip() for x in
           (msg or '오늘도 함께 행복하자').splitlines()
           if x.strip()][:3]

    size=int(W*.034)

    font_data = FONT.read_bytes()

    while size > 24:
        font = ImageFont.truetype(io.BytesIO(font_data), size)
        if all(d.textbbox((0, 0), x, font=font)[2] < W * .8 for x in lines):
            break
        size -= 2

    for i,x in enumerate(lines):
        d.text(
            (W//2,int(H*.695)+i*size*1.3),
            x,font=font,fill='#503822',anchor='mm'
        )

    name=f'final_{int(time.time()*1000)}.jpg'
    f.save(OUT/name,quality=97)
    return name


def base_url():
    render_url=os.environ.get('RENDER_EXTERNAL_URL')
    if render_url:
        return render_url.rstrip('/')
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.connect(('8.8.8.8',80))
        x=s.getsockname()[0]
        s.close()
        return f'http://{x}:8080'
    except:
        return 'http://127.0.0.1:8080'


def make_qr(file):
    n=f'qr_{int(time.time()*1000)}.png'
    qrcode.make(f'{base_url()}/photo?file={file}').save(OUT/n)
    return n

def choose(n):
    global sel
    sel=n
    ui.navigate.to('/camera')


@ui.page('/')
def home():
    with ui.column().classes(
        'w-full min-h-screen items-center justify-center gap-8'
    ):
        ui.label('🌿 영산강 AI 포토부스').classes(
            'text-6xl font-bold'
        )
        ui.label('우리 가족만의 특별한 영산강 추억').classes(
            'text-2xl text-gray-500'
        )
        ui.button(
            '📸 체험 시작',
            on_click=lambda:ui.navigate.to('/background')
        ).classes('text-3xl px-16 py-5')


@ui.page('/background')
def backgrounds():
    ui.label(
        '마음에 드는 영산강을 골라주세요 🌿'
    ).classes(
        'text-5xl font-bold text-center w-full my-5'
    )

    with ui.grid(columns=4).classes(
        'w-[94vw] max-w-[1750px] mx-auto gap-5'
    ):
        for i in range(1,9):
            with ui.card():
                ui.image(f'/bg/bg_{i}.png').classes(
                    'w-full aspect-[3/2] object-cover'
                )
                ui.button(
                    N[i-1],
                    on_click=lambda i=i:choose(i)
                ).classes('w-full text-xl')


@ui.page('/camera')
def camera():
    with ui.column().classes('w-full items-center gap-3'):

        ui.label(N[sel-1]).classes(
            'text-4xl font-bold'
        )

        ui.html('''
        <div style="
        width:1000px;max-width:90vw;aspect-ratio:3/2;
        overflow:hidden;border-radius:20px;background:#000">

        <video id="cam" autoplay playsinline muted
        style="
        width:100%;height:100%;object-fit:cover;
        transform:scaleX(-1)">
        </video>

        </div>

        <canvas id="cv" style="display:none"></canvas>
        ''')

        ui.run_javascript("""
        (async()=>{
            window.st?.getTracks().forEach(t=>t.stop());

            window.st=await navigator.mediaDevices.getUserMedia({
                video:true,
                audio:false
            });

            document.getElementById('cam').srcObject=window.st;
        })()
        """)

        c=ui.label('').classes('text-7xl font-bold')

        ui.button(
            '📸 촬영하기',
            on_click=lambda:shoot(c)
        ).classes('text-2xl px-16')


async def shoot(c):

    await ui.run_javascript("""
    window.ac=window.ac||
    new(window.AudioContext||window.webkitAudioContext)();
    window.ac.resume()
    """)

    for n in '321':
        c.set_text(n)

        await ui.run_javascript("""
        (() => {
            let a=window.ac,o=a.createOscillator(),g=a.createGain();
            o.connect(g);g.connect(a.destination);
            o.frequency.value=850;
            g.gain.value=.25;
            o.start();
            o.stop(a.currentTime+.15);
        })()
        """)

        await ui.run_javascript(
            'new Promise(r=>setTimeout(r,700))'
        )

    c.set_text('📸 찰칵!')

    data=await ui.run_javascript("""
    (() => {
        let v=document.getElementById('cam');
        let c=document.getElementById('cv');
        let x=c.getContext('2d');

        let w=v.videoWidth,h=v.videoHeight;
        let sx=0,sy=0,sw=w,sh=h;

        if(w/h>1.5){
            sw=h*1.5;
            sx=(w-sw)/2;
        }else{
            sh=w/1.5;
            sy=(h-sh)/2;
        }

        c.width=1200;
        c.height=800;

        x.save();
        x.translate(1200,0);
        x.scale(-1,1);
        x.drawImage(v,sx,sy,sw,sh,0,0,1200,800);
        x.restore();

        return c.toDataURL('image/jpeg',.95);
    })()
    """)

    await ui.run_javascript(
        "window.st?.getTracks().forEach(t=>t.stop())"
    )

    c.set_text('✨ AI 합성 중...')

    p=cv2.imdecode(
        np.frombuffer(
            base64.b64decode(data.split(',')[1]),
            np.uint8
        ),1
    )

    r = await asyncio.to_thread(cut, p, sel)
    n=f'photo_{int(time.time()*1000)}.jpg'

    cv2.imencode('.jpg',r)[1].tofile(str(OUT/n))

    ui.navigate.to(f'/decorate?file={n}')


@ui.page('/decorate')
def decorate(file=''):

    with ui.column().classes(
        'w-full items-center gap-4'
    ):

        ui.label(
            '소중한 추억을 글로 남겨주세요 🌿'
        ).classes('text-4xl font-bold')

        ui.image(f'/out/{file}').classes(
            'w-[650px] max-w-[70vw] rounded-xl'
        )

        msg=ui.textarea(
            placeholder='오늘의 소중한 추억을 남겨주세요'
        ).props(
            'outlined maxlength=60 counter'
        ).classes(
            'w-[850px] max-w-[90vw]'
        ).style(
            'min-height:140px;font-size:18px'
        )

        def done():
            n=frame(file,msg.value)
            ui.navigate.to(f'/wait?file={n}')

        ui.button(
            '✨ 완성하기',
            on_click=done
        ).classes('text-2xl px-16')


# ★ 완성사진 + BGM 10초
@ui.page('/wait')
def wait(file=''):

    # ★ 파일 자체를 base64로 읽음
    path=OUT/file

    if not path.exists():
        ui.label('사진 파일을 찾을 수 없습니다.')
        return

    data=base64.b64encode(
        path.read_bytes()
    ).decode()

    with ui.column().classes(
        'w-full min-h-screen items-center justify-center gap-3'
    ):

        ui.label(
            '✨ 우리의 영산강 추억이 완성됐어요'
        ).classes('text-4xl font-bold')

        # ★ 주소가 아니라 사진 자체를 직접 표시
        ui.html(f'''
        <img
        src="data:image/jpeg;base64,{data}"
        style="
        height:700px;
        max-height:75vh;
        max-width:90vw;
        width:auto;
        object-fit:contain;
        border-radius:18px;
        box-shadow:0 8px 30px rgba(0,0,0,.2)">
        ''')

        ui.label(
            '🎵 잠시 후 QR코드가 나타나요'
        ).classes('text-xl text-gray-500')

        ui.html(
            '<audio id="music" src="/bgm/bgm1.mp3" preload="auto"></audio>'
        )

        async def start():
            await ui.run_javascript("""
            (() => {
                let a=document.getElementById('music');

                if(a){
                    a.currentTime=0;
                    a.volume=.9;
                    a.play().catch(()=>{});
                }
            })()
            """)

        ui.timer(.3,start,once=True)

        # ★ 사진을 10초 보여준 후 QR
        ui.timer(
            10.3,
            lambda:ui.navigate.to(f'/qr?file={file}'),
            once=True
        )


@ui.page('/qr')
def qr(file=''):

    q=make_qr(file)

    with ui.column().classes(
        'w-full min-h-screen items-center justify-center gap-6'
    ):

        with ui.row().classes(
            'items-center justify-center gap-16'
        ):

            # 왼쪽 완성사진
            ui.image(f'/out/{file}').classes(
                'h-[650px] max-h-[72vh] '
                'w-auto object-contain shadow-xl'
            )

            # 오른쪽 QR
            ui.image(f'/out/{q}').classes(
                'w-[400px] h-[400px]'
            )

        ui.label(
            '📷 카메라로 스캔하고 소중한 추억을 가져가세요~'
        ).classes(
            'text-3xl font-bold whitespace-nowrap'
        )

        ui.button(
            '🏠 체험 마치기',
            on_click=lambda:ui.navigate.to('/')
        ).classes('text-xl px-12')


@ui.page('/photo')
def photo(file=''):

    with ui.column().classes(
        'w-full items-center gap-4 p-4'
    ):

        ui.label(
            '🌿 2026 영산강축제'
        ).classes('text-3xl font-bold')

        ui.image(f'/out/{file}').classes(
            'w-full max-w-[520px]'
        )

        ui.button(
            '⬇️ 사진 저장하기',
            on_click=lambda:ui.download(f'/out/{file}')
        ).classes('text-xl')


ui.run(
    title='영산강 AI 포토부스',
    host='0.0.0.0',
    port=int(os.environ.get('PORT', 8080)),
    reload=False
)
