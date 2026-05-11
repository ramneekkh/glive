import os
import asyncio
import base64
import io
import traceback
from aiohttp import web
import json

from google import genai
from google.genai import types

MODEL = "models/gemini-3.1-flash-live-preview"

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
    9.  **การใช้คำลงท้าย (Polite Particles):** คุณต้องใช้คำลงท้ายให้สอดคล้องกับเสียงของคุณ หากคุณใช้เสียงผู้หญิง (Female voice) คุณต้องใช้คำลงท้ายว่า 'ค่ะ' หรือ 'คะ' เท่านั้น และห้ามใช้ 'ครับ' โดยเด็ดขาด หากคุณใช้เสียงผู้ชาย (Male voice) คุณต้องใช้คำลงท้ายว่า 'ครับ' เท่านั้น และห้ามใช้ 'ค่ะ' หรือ 'คะ' โดยเด็ดขาด โปรดเลือกใช้ให้สอดคล้องกันตลอดการสนทนา
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
  </taskflow>
""")]
    ),
)

class AudioRelay:
    def __init__(self):
        self.gemini_session = None
        self.client = None

    async def wshandler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        print("Browser connected via WebSocket")
        
        try:
            # Wait for the first message which should be setup
            message = await ws.receive_str()
            data = json.loads(message)
            
            if data.get("type") != "setup":
                print("Error: First message was not setup")
                await ws.close(code=4001, message=b"Expected setup message")
                return ws
                
            api_key = data.get("apiKey")
            if not api_key:
                print("Error: No API key provided in setup message")
                await ws.close(code=4000, message=b"Missing API Key")
                return ws
                
            print("Received API Key, initializing Gemini client...")
            self.client = genai.Client(
                http_options={"api_version": "v1beta"},
                api_key=api_key,
            )
            
            async with self.client.aio.live.connect(model=MODEL, config=CONFIG) as session:
                self.gemini_session = session
                print("Connected to Gemini Live API")
                
                # Spawn tasks to handle bidirectional flow
                done, pending = await asyncio.wait(
                    [
                        asyncio.create_task(self.relay_from_browser(ws)),
                        asyncio.create_task(self.send_to_browser(ws))
                    ],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                
                for task in pending:
                    task.cancel()
                    
        except Exception as e:
            print("Error in relay session:", e)
            traceback.print_exc()
        finally:
            print("Browser disconnected or session ended")
            
        return ws

    async def relay_from_browser(self, ws):
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if "realtimeInput" in data:
                        chunks = data["realtimeInput"].get("mediaChunks", [])
                        for chunk in chunks:
                            mime_type = chunk.get("mimeType")
                            b64_data = chunk.get("data")
                            if b64_data:
                                raw_data = base64.b64decode(b64_data)
                                # Use send_realtime_input with audio= keyword argument
                                await self.gemini_session.send_realtime_input(audio={"data": raw_data, "mime_type": mime_type})
                elif msg.type == web.WSMsgType.ERROR:
                    print('ws connection closed with exception %s' % ws.exception())
        except Exception as e:
            print("Error forwarding to Gemini:", e)

    async def send_to_browser(self, ws):
        try:
            while True:
                turn = self.gemini_session.receive()
                async for response in turn:
                    msg = {}
                    if data := response.data:
                        msg = {
                            "serverContent": {
                                "modelTurn": {
                                    "parts": [
                                        {
                                            "inlineData": {
                                                "mimeType": "audio/pcm",
                                                "data": base64.b64encode(data).decode()
                                            }
                                        }
                                    ]
                                }
                            }
                        }
                    elif text := response.text:
                        msg = {
                            "serverContent": {
                                "modelTurn": {
                                    "parts": [
                                        {
                                            "text": text
                                        }
                                    ]
                                }
                            }
                        }
                    
                    if msg:
                        await ws.send_str(json.dumps(msg))
                        
                await asyncio.sleep(0.01)
        except Exception as e:
            print("Error receiving from Gemini or sending to browser:", e)

async def index(request):
    return web.FileResponse('./index.html')

def create_app():
    app = web.Application()
    relay = AudioRelay()
    app.add_routes([
        web.get('/', index),
        web.get('/ws', relay.wshandler),
        web.static('/', './') # Serve other static files from current dir
    ])
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 8080))
    print(f"Starting server on port {port}")
    web.run_app(app, host='0.0.0.0', port=port)
