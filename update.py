import requests
import json
from lxml import etree
import re
import traceback
import os
route = None
is_no_update = True

def load_update_config():
    global route
    with open("./rank/route.json","r",encoding="utf8")as fp:
        route = json.load(fp)

def process_rank_update(rank_route:str, rank_list:dict):
    for rank_sheet in rank_list.keys():
        rank_file_path = f"./rank/auto_update/{rank_route}/{rank_sheet}.png"
        #rank_file_path = f"{rank_sheet}.png"
        print(f"Downloading {rank_list[rank_sheet]}")
        resp = requests.get(rank_list[rank_sheet])
        res = resp.content
        with open(rank_file_path,"wb") as rank_file:
            rank_file.write(res)

def get_rank_list(artical_id:int,rank_level:str):
    resp = requests.get(f"https://www.bilibili.com/read/cv{str(artical_id)}")
    res = resp.text
    html = etree.HTML(res)
    artical_data = html.xpath("/html/body/div[2]/div[5]")[0]
    #artical_data = html.xpath('//figure')
    imgs = artical_data.xpath("//img")
    img_list = []
    for img_element in imgs:
        if "data-src" in img_element.attrib:
            img_list.append(f'https:{img_element.attrib["data-src"]}')
    #print(img_list)
    rank_list = {}
    count = 0
    for img_url in img_list:
        count += 1
        rank_list[f"{rank_level}_{str(count)}"] = img_url
    return rank_list

def check_update(rank_route:str):
    global is_no_update
    config_path = f"./rank/auto_update/{rank_route}/auto_update_config.json"
    with open(config_path,"r",encoding="utf8")as fp:
        rank_conf = json.load(fp)
    mid = rank_conf["mid"]
    last_id = rank_conf["last_check_id"]
    title_re = rank_conf["title_re"]
    title_rank_re_pos = rank_conf["rank_name_pos"]
    print(f"start check {mid}")
    headers = {
        "referer" : "https://space.bilibili.com/",
        ":authority" : "api.bilibili.com",
        "user-agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"
    }
    try:
        is_update_success = False
        is_stop_check = False
        for artical_page in range(1,5):
            if is_stop_check:
                break
            resp = requests.get(f"https://api.bilibili.com/x/space/article?mid={mid}&pn={str(artical_page)}&ps=12&sort=publish_time&jsonp=jsonp")
            result = resp.json()
            if result["code"]!=0:
                print("返回code出错")
            articals = result["data"]["articles"]
            for artical in articals:
                if is_stop_check:
                    break
                if artical["id"] <= last_id:
                    is_stop_check = True
                    break
                title = artical["title"]
                searchObj = re.search(title_re, title, re.M|re.I)
                if searchObj == None:
                    continue
                rank_level = searchObj.group(title_rank_re_pos)
                rank_list = get_rank_list(artical["id"],rank_level)
                process_rank_update(rank_route, rank_list)
                #更新环境变量
                is_no_update = False
                #更新配置文件
                rank_conf["last_check_id"] = artical["id"]
                with open(config_path,'r+',encoding='utf8')as fp:
                    fp.seek(0)
                    fp.truncate()
                    json.dump(rank_conf,fp,indent=4,ensure_ascii=False)
                rank_config_path = f"./rank/auto_update/{rank_route}/config.json"
                with open(rank_config_path,"r",encoding="utf8")as fp:
                    rank_config = json.load(fp)
                rank_file_list = []
                for rank_name in rank_list.keys():
                    rank_file_list.append(f"{rank_name}.png")
                rank_str = rank_file_list[0].replace("_1.png","")
                rank_config["notice"] = rank_conf["notice_template"].replace("{$rank}",rank_str)
                rank_config["files"] = rank_file_list
                with open(rank_config_path,'r+',encoding='utf8')as fp:
                    fp.seek(0)
                    fp.truncate()
                    json.dump(rank_config,fp,indent=4,ensure_ascii=False)
                is_update_success = True
                is_stop_check = True
        if is_update_success:
            print(f"success update {mid}")
        else:
            print(f"success check {mid}, no update")
    except:
        print(traceback.print_exc())
        print(f"check error at {mid}")

def process_check():
    areas = route["ranks"]["channels"]["auto_update"]
    for area in areas:
        area_conf = areas[area]
        for rank_obj in area_conf:
            route_path = rank_obj["route"]
            check_update(route_path)


load_update_config()
process_check()
if is_no_update:
    exit(1)