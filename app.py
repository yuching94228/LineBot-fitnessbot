# 引用套件
from os import environ
from flask import Flask, request, abort
from urllib.parse import parse_qs
import json
import psycopg2
from datetime import datetime,timezone,timedelta

from linebot import (
   LineBotApi, WebhookHandler
)
from linebot.exceptions import (
   InvalidSignatureError
)
from linebot.models import *

app = Flask(__name__)

line_bot_api = LineBotApi(environ['CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(environ['CHANNEL_SECRET'])

def db_execute(sqlcmd,parmater_tuple):

    con = psycopg2.connect(
        host=environ['FITNESSDB_HOST'],
        database="fitnessbotDB"
        user=environ['FITNESSDB_USER'],
        password=environ['FITNESSDB_PW']
    )

    cursor = con.cursor()
    cursor.execute(sqlcmd, parmater_tuple)
    con.commit()
    con.close()

def db_selecet(sqlcmd,parmater_tuple=None):

    con = psycopg2.connect(
        host=environ['FITNESSDB_HOST'],
        database="fitnessbotDB"
        user=environ['FITNESSDB_USER'],
        password=environ['FITNESSDB_PW']
    )

    cursor = con.cursor()
    cursor.execute(sqlcmd,parmater_tuple)
    records = cursor.fetchall()
    con.close()

    return records

def get_datetime():
    dt1 = datetime.utcnow().replace(tzinfo=timezone.utc)
    dt2 = dt1.astimezone(timezone(timedelta(hours=8)))  # 轉換時區 -> 東八區

    return dt2

def get_menu_id(manu_num):
    with open(f"material/rich_menu/{manu_num}/id.txt", encoding="utf8") as f:
        manu_id = f.read()
    return manu_id

def detect_json_array_to_new_message_array(action_name):
    with open(f"material/{action_name}/reply.json", encoding="utf8") as f:
         jsonArray = json.load(f)

    # 解析json
    returnArray = []
    for jsonObject in jsonArray:

        # 讀取其用來判斷的元件
        message_type = jsonObject.get('type')

        # 轉換
        if message_type == 'text':
            returnArray.append(TextSendMessage.new_from_json_dict(jsonObject))
        elif message_type == 'imagemap':
            returnArray.append(ImagemapSendMessage.new_from_json_dict(jsonObject))
        elif message_type == 'template':
            returnArray.append(TemplateSendMessage.new_from_json_dict(jsonObject))
        elif message_type == 'image':
            returnArray.append(ImageSendMessage.new_from_json_dict(jsonObject))
        elif message_type == 'sticker':
            returnArray.append(StickerSendMessage.new_from_json_dict(jsonObject))
        elif message_type == 'audio':
            returnArray.append(AudioSendMessage.new_from_json_dict(jsonObject))
        elif message_type == 'location':
            returnArray.append(LocationSendMessage.new_from_json_dict(jsonObject))
        elif message_type == 'flex':
            returnArray.append(FlexSendMessage.new_from_json_dict(jsonObject))
        elif message_type == 'video':
            returnArray.append(VideoSendMessage.new_from_json_dict(jsonObject))

            # 回傳
    return returnArray

@app.route("/callback", methods=['POST'])
def callback():
   # get X-Line-Signature header value
   signature = request.headers['X-Line-Signature']

   # get request body as text
   body = request.get_data(as_text=True)
   app.logger.info("Request body: " + body)

   db_execute(
       """INSERT INTO public."EVENT_LOG"("LOG","CDT") VALUES(%s,%s at time zone 'UTC-8')""",
       (body,  get_datetime()))


   # handle webhook body
   try:
       handler.handle(body, signature)
   except InvalidSignatureError:
       print("Invalid signature. Please check your channel access token/channel secret.")
       abort(400)

   return 'OK'

# 用戶關注
@handler.add(FollowEvent)
def process_follow_event(event):
    profile = line_bot_api.get_profile(event.source.user_id)

    result_message_array = detect_json_array_to_new_message_array("follow")

    # 消息發送
    line_bot_api.reply_message(
       event.reply_token,
       result_message_array
    )

    db_execute("INSERT INTO public.\"USER\"(DISPLAY_NAME,USER_ID,PICTURE_URL,STATUS_MESSAGE,LANGUAGE) VALUES(%s,%s,%s,%s,%s)",
    (profile.display_name,profile.user_id,profile.picture_url,profile.status_message,profile.language))

    line_bot_api.link_rich_menu_to_user(event.source.user_id, get_menu_id("000"))

def personal_info_setting(event):

    line_bot_api.reply_message(event.reply_token,TextSendMessage("請輸入您的身高/體重/年齡🙇\n(ex) 170/60/30"))
    db_execute("UPDATE public.\"USER\" SET \"INPUT_STATUS\"=\'INPUTWEIGHT\'  WHERE user_id=\'"+event.source.user_id+"\'",
        ())

@handler.add(PostbackEvent)
def process_postback_event(event):
    # 把POSTBACK暗傳的資料取出來
    query_string_dict = parse_qs(event.postback.data)

    # 點選個人資料設定
    if query_string_dict.get('action')[0] == "personal_setting":
        personal_info_setting(event)

    if query_string_dict.get('action')[0][:4] == "food":
        food_type = query_string_dict.get('action')[0][5:]
        db_execute(
            """INSERT INTO public."USER_FOOD"("USER_ID", "FOOD_TYPE", "FOOD_G", "CDT") VALUES(%s,%s,%s,%s at time zone 'UTC-8')""",
            (event.source.user_id, food_type , None , get_datetime()))
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage("請輸入g數🙇\n(ex)50g"))

    if query_string_dict.get('action')[0][:5] == "water":
        water_type = query_string_dict.get('action')[0][6:]
        db_execute(
            """INSERT INTO public."USER_WATER"("USER_ID", "WATER_TYPE", "WATER_ML", "CDT") VALUES(%s,%s,%s,%s at time zone 'UTC-8')""",
            (event.source.user_id, water_type , None , get_datetime()))
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage("請輸入飲用ml數🙇\n(ex)200ml"))

    if query_string_dict.get('action')[0] == "record_exercise":

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage("功能尚未開放\n敬請期待😆😆😆"))

    if query_string_dict.get('action')[0] == "search_today" or query_string_dict.get('action')[0] == "search_his":

        dt = get_datetime()
        if query_string_dict.get('action')[0][7:]=='today':
            dt = get_datetime()
        elif query_string_dict.get('action')[0][7:]=='his':
            dt = datetime.strptime(event.postback.params['date'], "%Y-%m-%d")

        search_result = db_selecet(
        """SELECT "TDEE", "BMR", "WATER",FOOD_CAL,WATER_ML_ACT FROM(SELECT "TDEE", "BMR", "WATER" """+
	    """ FROM public."USER" where "user_id"=%s) AS A"""+
        """ ,(SELECT SUM("FOOD_CAL") FOOD_CAL"""+
        """ FROM public."USER_FOOD" where "USER_ID"=%s AND TO_CHAR("CDT",'YYYY/MM/DD')=%s) AS B"""+
        """ ,(SELECT SUM("WATER_ML_ACT") WATER_ML_ACT"""+
        """ FROM public."USER_WATER" where "USER_ID"=%s AND TO_CHAR("CDT",'YYYY/MM/DD')=%s) AS C"""
        ,(event.source.user_id,event.source.user_id,dt.strftime('%Y/%m/%d'),event.source.user_id,dt.strftime('%Y/%m/%d')))

        if search_result[0][3]==None and search_result[0][4]==None:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(dt.strftime('%Y/%m/%d')+"查無資料"))
        else:
            tdee = search_result[0][0]
            bmr = search_result[0][1]
            water = search_result[0][2]
            if search_result[0][3]==None : food_cal=0
            else: food_cal = search_result[0][3]
            if search_result[0][4] == None : water_ml_act=0
            else: water_ml_act= search_result[0][4]

            reply_array = []
            reply_array.append(TextSendMessage(f"{dt.strftime('%Y/%m/%d')}的查詢結果\n📌攝取熱量為:{food_cal}kcal\n📌與TDEE差距{tdee-food_cal}kcal\n📌飲水量為:{water_ml_act}ml\n📌與建議飲水量差距{water-water_ml_act}ml"))
            # if food_cal >= tdee:
            #     reply_array.append(TextSendMessage("已攝取超過TDEE"))
            #     reply_array.append(StickerSendMessage.new_from_json_dict("""{"type": "sticker","packageId": "11537","stickerId": "52002752"}"""))
            # else:
            #     reply_array.append(TextSendMessage("尚未達到TDEE"))
            #     reply_array.append(StickerSendMessage.new_from_json_dict(
            #         """{"type": "sticker","packageId": "11537","stickerId": "52002752"}"""))
            if water_ml_act >= water:
                reply_array.append(TextSendMessage("恭喜水分達標~"))
                reply_array.append(StickerSendMessage.new_from_json_dict(json.loads("""{"type": "sticker","packageId": "11537","stickerId": "52002752"}""")))
            else:
                reply_array.append(TextSendMessage("水分未達標,加油加油~"))
                reply_array.append(StickerSendMessage.new_from_json_dict(json.loads("""{"type": "sticker","packageId": "11538","stickerId": "51626503"}""")))

            line_bot_api.reply_message(
                event.reply_token,
                reply_array)

    elif query_string_dict.get('action')[0] == "suggest_info":
        # line_bot_api.link_rich_menu_to_user(event.source.user_id, get_menu_id("05"))
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage("請從下方選單處選擇您想瀏覽的資訊🙇"))

    elif query_string_dict.get('action')[0] == "info_food":
        result_message_array = detect_json_array_to_new_message_array("info_food")
        # 消息發送
        line_bot_api.reply_message(
            event.reply_token,
            result_message_array
        )

    elif query_string_dict.get('action')[0] == "info_exercise":
        result_message_array = detect_json_array_to_new_message_array("info_exercise")

        # 消息發送
        line_bot_api.reply_message(
            event.reply_token,
            result_message_array
        )

    # 若有menu欄位,做以下功能
    # 更換用戶圖文選單
    if 'menu' in query_string_dict:
        replyJsonPath = query_string_dict.get('menu')[0]

        # 綁定圖文選單
        line_bot_api.link_rich_menu_to_user(event.source.user_id, get_menu_id(replyJsonPath))

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    if '/' in event.message.text:
        userinfo_text = event.message.text.split("/")
        # line_bot_api.reply_message(event.reply_token, TextSendMessage(f"您的身高為:{userinfo_text[0]},體重為{userinfo_text[1]},年齡為{userinfo_text[2]}"))
        db_execute(
            "UPDATE public.\"USER\" SET \"AGE\"=%s,\"WEIGHT\"=%s,\"HEIGHT\"=%s ,\"INPUT_STATUS\"=\'INPUTGENDER\' WHERE user_id=\'" + event.source.user_id + "\'",
            (userinfo_text[2],userinfo_text[1],userinfo_text[0]))
        result_message_array = detect_json_array_to_new_message_array("gender")

        # 消息發送
        line_bot_api.reply_message(
            event.reply_token,
            result_message_array
        )
    elif event.message.text == "您選擇了女性" or event.message.text == "您選擇了男性":
        if event.message.text == "您選擇了男性":
            gender = '1'
        else:
            gender = '2'

        db_execute(
            "UPDATE public.\"USER\" SET \"GENDER\"=%s ,\"INPUT_STATUS\"=\'INPUTEXERCISE\' WHERE user_id=\'" + event.source.user_id + "\'",
            (gender))
        result_message_array = detect_json_array_to_new_message_array("select_exercise")

        # 消息發送
        line_bot_api.reply_message(
            event.reply_token,
            result_message_array
        )
    elif event.message.text[:3] == "運動量":
        exercise_rate = 0
        if event.message.text[4:] == "久坐":
            exercise_rate = 1.2
        elif event.message.text[4:] == "輕量活動":
            exercise_rate = 1.375
        elif event.message.text[4:] == "中度活動量":
            exercise_rate = 1.55
        elif event.message.text[4:] == "高度活動量":
            exercise_rate = 1.725
        elif event.message.text[4:] == "非常高度活動量":
            exercise_rate = 1.9

        db_execute(
            "UPDATE public.\"USER\" SET \"EXERCISE_RATE\"=\'"+ str(exercise_rate) +"\' ,\"INPUT_STATUS\"=\'CALCUTDEE\' WHERE user_id=\'" + event.source.user_id + "\'",
            "")

        person_info = db_selecet("""SELECT "WEIGHT", "HEIGHT", "AGE", "EXERCISE_RATE","GENDER" FROM public."USER" WHERE user_id='"""+ event.source.user_id +"\'")

        # 計算TDEE
        tdee=0
        bmr=0
        if person_info[0][4] == 1:
            bmr = ((10 * int(person_info[0][0])) + (6.25 * int(person_info[0][1]) - (5 * int(person_info[0][2]))) + 5)
        elif person_info[0][4] == 2:
            bmr = ((10 * int(person_info[0][0])) + (6.25 * int(person_info[0][1]) - (5 * int(person_info[0][2]))) - 161)

        water = int(person_info[0][0]) * 30
        tdee = bmr * float(person_info[0][3])

        tdee = round(tdee,2)
        bmr = round(bmr, 2)

        db_execute(
            "UPDATE public.\"USER\" SET \"WATER\"=\'" + str(water) + "\', \"TDEE\"=\'" + str(tdee) + "\',\"BMR\"=\'" + str(bmr) + "\' ,\"INPUT_STATUS\"=\'SETTINGDONE\' WHERE user_id=\'" + event.source.user_id + "\'",
            "")

        # 消息發送
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage("您的\n📌BMR基礎代謝:" + str(bmr)+
                            "\n📌TDEE總消耗:"+str(tdee) +  "\n📌建議飲水量:" + str(water) + "ml\n已為您設定完成🙇")
        )
        # 綁定首頁選單
        line_bot_api.link_rich_menu_to_user(event.source.user_id, get_menu_id("00"))

    elif event.message.text[-2:] == "ml":

        water_ml = event.message.text[:-2]
        water_rate = 0
        water_type_str = ""
        water_type = db_selecet(
            """SELECT "WATER_TYPE" FROM  public."USER_WATER" WHERE "USER_ID" = %s AND "CDT"="""+
            """(select max("CDT") from public."USER_WATER" where "USER_ID" = %s AND "WATER_ML" IS NULL)""", (event.source.user_id,event.source.user_id) )

        if water_type[0][0].strip() == '0':
            water_rate = 100
            water_type_str = "水"
        elif water_type[0][0].strip() == '1':
            water_rate = 98
            water_type_str = "茶"
        elif water_type[0][0].strip() == "2":
            water_rate = 90
            water_type_str = "咖啡"
        elif water_type[0][0].strip() == "3":
            water_rate = 88
            water_type_str = "鮮奶"
        elif water_type[0][0].strip() == "4":
            water_rate = 91
            water_type_str = "豆漿"
        elif water_type[0][0].strip() == "5":
            water_rate = 95
            water_type_str = "湯"
        elif water_type[0][0].strip() == "6":
            water_rate = 96
            water_type_str = "運動飲料"
        elif water_type[0][0].strip() == "7":
            water_rate = 89
            water_type_str = "檸檬水"
        elif water_type[0][0].strip() == "8":
            water_rate = 85
            water_type_str = "蛋白飲"
        elif water_type[0][0].strip() == "9":
            water_rate = 86
            water_type_str = "碳酸飲料"
        elif water_type[0][0].strip() == "10":
            water_rate = 80
            water_type_str = "手搖杯"

        water_ml_act = round(int(water_ml) * water_rate / 100)

        db_execute(
            """UPDATE public."USER_WATER" SET "WATER_ML"=%s , "WATER_ML_ACT"=%s WHERE "USER_ID" = %s """ +
            """AND "CDT" = (select max("CDT") from public."USER_WATER" where "USER_ID" = %s AND "WATER_ML" IS NULL)  """
            ,(water_ml,water_ml_act,event.source.user_id,event.source.user_id))

        # 消息發送
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage("紀錄完成\n📌" + water_type_str + "的攝取比率:" + str(water_rate) +
                            "%\n📌實際攝取水量為:" + str(water_ml_act) + "ml\n已新增完成🙇")
        )
    elif event.message.text[-1:] == "g":

        food_g = event.message.text[:-1]
        food_type_str = ""
        food_cal_rate = 0
        food_cal = 0
        food_type = db_selecet(
            """SELECT "FOOD_TYPE" FROM  public."USER_FOOD" WHERE "USER_ID" = %s AND "CDT"="""+
            """(select max("CDT") from public."USER_FOOD" where "USER_ID" = %s AND "FOOD_G" IS NULL)""", (event.source.user_id,event.source.user_id) )

        if food_type[0][0].strip() == '1':
            food_cal_rate = 4
            food_type_str = "蛋白質"
        elif food_type[0][0].strip() == '2':
            food_cal_rate = 9
            food_type_str = "脂肪"
        elif food_type[0][0].strip() == "3":
            food_cal_rate = 4
            food_type_str = "碳水化合物"

        food_cal = int(food_g) * food_cal_rate

        db_execute(
            """UPDATE public."USER_FOOD" SET "FOOD_G"=%s , "FOOD_CAL"=%s WHERE "USER_ID" = %s """ +
            """AND "CDT" = (select max("CDT") from public."USER_FOOD" where "USER_ID" = %s AND "FOOD_G" IS NULL)  """
            ,(food_g,food_cal,event.source.user_id,event.source.user_id))

        # 消息發送
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage("紀錄完成\n📌" + food_type_str + "每克熱量:" + str(food_cal_rate) +
                            "kcal\n📌攝取熱量為:" + str(food_cal) + "kcal\n已新增完成🙇")
        )
    elif event.message.text == "初始個人設定":
        personal_info_setting(event)
    # elif event.message.text != '':
    #     # 消息發送
    #     line_bot_api.reply_message(
    #         event.reply_token,
    #         TextSendMessage("無法判斷輸入的資訊\n請重新由選單選擇或重新輸入🙇")
    #     )

# @handler.add(MessageEvent,message=ImageMessage)
# def handle_image_message(event):
#
#    # line_bot_api get message content python
#    message_content = line_bot_api.get_message_content(event.message.id)
#    file_path = event.message.id +'.jpg'
#    with open(file_path, 'wb') as fd:
#        for chunk in message_content.iter_content():
#            fd.write(chunk)

if __name__ == "__main__":
    # app.run(host='0.0.0.0')
    app.run(host='0.0.0.0',port = environ['PORT'])
    # app.run()


