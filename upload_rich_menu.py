import json
import os
from os import environ
from linebot import LineBotApi
from linebot.models import RichMenu

option = 0

while(option!=9):
    option = int(input("(1)上傳圖文選單\n(2)刪除圖文選單\n(3)查詢目前圖文選單\n(9)離開\n請輸入執行選項:"))

    # 記得設定環境變數
    line_bot_api = LineBotApi(environ['CHANNEL_ACCESS_TOKEN'])

    if option == 1:
        # 這邊的位址請記得放入"相同檔名的"[.jpg]以及[.json]兩個檔案在同路徑底下
        print("這邊的位址請記得放入<相同檔名>的[.jpg]以及[.json]兩個檔案在同路徑底下")
        file_address = input("請輸入路徑+檔名(ex)material\\rich_menu\\[檔名]:")

        with open(file_address+'.json', encoding="utf8") as f:
            rich_menu_json = json.load(f)

        # 創建圖文選單，取得menuId
        lineRichMenuId = line_bot_api.create_rich_menu(rich_menu=RichMenu.new_from_json_dict(rich_menu_json))
        print("-設定檔上傳結果",lineRichMenuId)

        # 上傳照片至該menu-id
        set_image_response = ''
        with open(file_address+'.jpg', 'rb') as f:
            set_image_response = line_bot_api.set_rich_menu_image(lineRichMenuId, 'image/jpeg', f)
        # 回傳none表示成功
        print("-圖片上傳結果",set_image_response)

    elif option == 2:
        del_menu_id = input("請輸入要刪除的lineRichMenuId:")
        deleteResult = line_bot_api.delete_rich_menu(del_menu_id)
        # 回傳none表示成功
        print(deleteResult)

    elif option == 3 :
        # 查詢帳號內擁有的圖文選單
        menu_list = line_bot_api.get_rich_menu_list()
        print("目前帳號內有的圖文選單ID")
        for menu_item in menu_list:
            print(menu_item.rich_menu_id)

    os.system("cls")