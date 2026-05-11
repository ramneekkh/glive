import os
import asyncio
import base64
import io
import traceback

import cv2
import pyaudio
import PIL.Image

import argparse

from google import genai
from google.genai import types

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

MODEL = "models/gemini-3.1-flash-live-preview"

DEFAULT_MODE = "camera"

client = genai.Client(
    http_options={"api_version": "v1beta"},
    api_key=os.environ.get("GEMINI_API_KEY"),
)

CONFIG = types.LiveConnectConfig(
    response_modalities=[
        "AUDIO",
    ],
    media_resolution="MEDIA_RESOLUTION_MEDIUM",
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr")
        )
    ),
    context_window_compression=types.ContextWindowCompressionConfig(
        trigger_tokens=104857,
        sliding_window=types.SlidingWindow(target_tokens=52428),
    ),
    system_instruction=types.Content(
        parts=[types.Part.from_text(text="""<role>
    คุณคือตัวแทน AI สนทนาภาษาไทยที่สุภาพและเป็นมิตรของธนาคารไทยพาณิชย์ (SCB) คุณมีหน้าที่หลักในการให้ข้อมูลและตอบคำถามเกี่ยวกับผลิตภัณฑ์และบริการของธนาคารตามข้อมูล FAQ ที่มีอยู่ คุณจะสื่อสารเป็นภาษาไทยเท่านั้นและไม่เข้าใจภาษาอังกฤษ
  </role>

  <persona>
    <primary_goal>
      ช่วยเหลือผู้ใช้ในการค้นหาข้อมูลและตอบคำถามเกี่ยวกับธนาคารไทยพาณิชย์อย่างถูกต้องและเป็นธรรมชาติที่สุด โดยใช้ภาษาไทยเป็นหลัก
    </primary_goal>
    <identity>
      ตัวแทน AI สนทนาของ SCB ที่เป็นมิตร สุภาพ และมีความรู้เกี่ยวกับผลิตภัณฑ์และบริการของธนาคารไทยพาณิชย์
    </identity>
    <guidelines>
      คุณต้องปฏิบัติตามข้อจำกัดและขั้นตอนการทำงานที่กำหนดไว้อย่างเคร่งครัด
      คุณจะทักทายผู้ใช้เป็นภาษาไทยเสมอ
      คุณเข้าใจสำเนียงภาษาไทย ความแตกต่างทางวัฒนธรรม และคำสแลงที่ใช้กันทั่วไป
      คุณสามารถปรับโทนเสียง (เป็นทางการ เห็นอกเห็นใจ หรือหนักแน่น) และความเร็วในการพูดให้เหมาะสมกับสถานการณ์
      คุณจะจัดการกับการขัดจังหวะของผู้ใช้ได้อย่างราบรื่นและรักษาบริบทของการสนทนาไว้
      คุณมีความฉลาดทางอารมณ์และสามารถจัดการกับผู้ใช้ที่โกรธหรือกังวลใจด้วยการตอบสนองที่เหมาะสม
      คุณจะตรวจจับการสิ้นสุดการพูดของผู้ใช้ได้อย่างน่าเชื่อถือ โดยไม่เกิดการตรวจจับผิดพลาดจากการหยุดชั่วคราวหรือเสียงรบกวนจากสิ่งแวดล้อม
      หากผู้ใช้สอบถามเกี่ยวกับหัวข้อที่ต้องห้าม เช่น ข้อมูลส่วนบุคคลที่ละเอียดอ่อน (PIN, OTP, รหัสผ่าน, เลขบัตรเครดิตเต็ม) หรือคำแนะนำทางการเงินเฉพาะเจาะจง คุณจะต้องปฏิเสธอย่างสุภาพและแนะนำให้ติดต่อ SCB Call Center
      หากผู้ใช้มีปัญหาด้านความปลอดภัยหรือเหตุฉุกเฉิน คุณจะต้องแนะนำให้ติดต่อ SCB Call Center ทันที
    </guidelines>
  </persona>

  <constraints>
    1.  **ภาษา:** คุณจะสื่อสารเป็นภาษาไทยเท่านั้นและไม่เข้าใจภาษาอังกฤษ หากผู้ใช้พูดภาษาอังกฤษ คุณจะแจ้งว่าคุณเข้าใจเฉพาะภาษาไทยเท่านั้น
    2.  **แหล่งข้อมูล:** ข้อมูลที่คุณให้จะต้องอ้างอิงจากเอกสาร FAQ ของ SCB ที่ได้รับมาเท่านั้น
    3.  **ข้อมูลเฉพาะเจาะจงและข้อมูลล่าสุด:** สำหรับคำถามที่ต้องการข้อมูลเฉพาะเจาะจงมากเกินกว่าที่ FAQ จะให้ได้ (เช่น อัตราดอกเบี้ยล่าสุด, ค่าธรรมเนียมที่อาจมีการเปลี่ยนแปลง) หรือต้องการคำแนะนำทางการเงินส่วนบุคคล คุณจะต้องแนะนำให้ผู้ใช้ติดต่อ SCB Call Center 0 2777 7777
    4.  **ข้อมูลส่วนบุคคล:** ห้ามขอหรือจัดเก็บข้อมูลส่วนบุคคลที่ละเอียดอ่อนจากผู้ใช้ เช่น รหัส PIN, OTP, รหัสผ่าน, หรือหมายเลขบัตรเครดิตเต็ม
    5.  **ความปลอดภัยและเหตุฉุกเฉิน:** หากผู้ใช้แจ้งปัญหาด้านความปลอดภัยหรือเหตุฉุกเฉิน คุณจะต้องแนะนำให้ติดต่อ SCB Call Center 0 2777 7777 ทันที
    6.  **วันที่ปัจจุบัน:** คุณจะถือว่าวันที่ปัจจุบันคือ 2026-05-09 สำหรับการอ้างอิงวันที่ใดๆ
    7.  **การให้คำแนะนำ:** ห้ามให้คำแนะนำการลงทุนหรือคำแนะนำทางการเงินที่เฉพาะเจาะจงโดยไม่อ้างอิงเอกสารทางการ
    8.  **การเปลี่ยนแปลงข้อมูล:** แจ้งผู้ใช้ว่าอัตราดอกเบี้ย ค่าธรรมเนียม และเงื่อนไขต่างๆ อาจมีการเปลี่ยนแปลง และควรอ้างอิงข้อมูลล่าสุดจากเว็บไซต์ scb.co.th สำหรับข้อมูลที่ถูกต้องที่สุด
  </constraints>

  <taskflow>
    These define the conversational subtasks that you can take. Each subtask has a sequence of steps that should be taken in order.
    <subtask name="Initial Engagement and Greeting">
      <step name="Greeting and Language Check">
        <trigger>User initiates conversation.</trigger>
        <action>
          1.  Greet the user warmly in Thai (e.g., "สวัสดีค่ะ/ครับ ยินดีต้อนรับสู่ธนาคารไทยพาณิชย์ มีอะไรให้ช่วยคะ/ครับ").
          2.  If the user speaks English, politely inform them that you only understand Thai (e.g., "ขออภัยค่ะ/ครับ ดิฉัน/ผมเข้าใจและสื่อสารได้เฉพาะภาษาไทยเท่านั้นค่ะ/ครับ").
        </action>
      </step>
    </subtask>
    <!-- ... other subtasks omitted for brevity ... -->
  </taskflow>""")],
        role="user"
    ),
)

pya = pyaudio.PyAudio()

class AudioLoop:
    def __init__(self, video_mode=DEFAULT_MODE):
        self.video_mode = video_mode
        self.audio_in_queue = None
        self.out_queue = None
        self.session = None
        self.audio_stream = None

    async def send_text(self):
        while True:
            text = await asyncio.to_thread(input, "message > ")
            if text.lower() == "q":
                break
            if self.session is not None:
                await self.session.send(input=text or ".", end_of_turn=True)

    def _get_frame(self, cap):
        ret, frame = cap.read()
        if not ret:
            return None
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PIL.Image.fromarray(frame_rgb)
        img.thumbnail([1024, 1024])
        image_io = io.BytesIO()
        img.save(image_io, format="jpeg")
        image_io.seek(0)
        image_bytes = image_io.read()
        return {"mime_type": "image/jpeg", "data": base64.b64encode(image_bytes).decode()}

    async def get_frames(self):
        cap = await asyncio.to_thread(cv2.VideoCapture, 0)
        while True:
            frame = await asyncio.to_thread(self._get_frame, cap)
            if frame is None:
                break
            await asyncio.sleep(1.0)
            if self.out_queue is not None:
                await self.out_queue.put(frame)
        cap.release()

    async def send_realtime(self):
        while True:
            if self.out_queue is not None:
                msg = await self.out_queue.get()
                if self.session is not None:
                    await self.session.send(input=msg)

    async def listen_audio(self):
        mic_info = pya.get_default_input_device_info()
        self.audio_stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )
        while True:
            data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, exception_on_overflow=False)
            if self.out_queue is not None:
                await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})

    async def receive_audio(self):
        while True:
            if self.session is not None:
                turn = self.session.receive()
                async for response in turn:
                    if data := response.data:
                        self.audio_in_queue.put_nowait(data)
                        continue
                    if text := response.text:
                        print(text, end="")
                while not self.audio_in_queue.empty():
                    self.audio_in_queue.get_nowait()

    async def play_audio(self):
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
        )
        while True:
            if self.audio_in_queue is not None:
                bytestream = await self.audio_in_queue.get()
                await asyncio.to_thread(stream.write, bytestream)

    async def run(self):
        try:
            async with (
                client.aio.live.connect(model=MODEL, config=CONFIG) as session,
                asyncio.TaskGroup() as tg,
            ):
                self.session = session
                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=5)

                # Run without text input task to avoid blocking in background
                # tg.create_task(self.send_text())
                tg.create_task(self.send_realtime())
                tg.create_task(self.listen_audio())
                if self.video_mode == "camera":
                    tg.create_task(self.get_frames())
                tg.create_task(self.receive_audio())
                tg.create_task(self.play_audio())

                # Keep running until cancelled
                while True:
                    await asyncio.sleep(1)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            traceback.print_exc()
        finally:
            if self.audio_stream is not None:
                self.audio_stream.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, default="none", choices=["camera", "none"])
    args = parser.parse_args()
    main = AudioLoop(video_mode=args.mode)
    asyncio.run(main.run())
