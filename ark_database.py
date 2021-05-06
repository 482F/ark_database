#!/usr/bin/env python3
import sys
import xml.etree.ElementTree as ET
import os
import getpass
import pymysql.cursors

SCRIPT_DIR = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
CONFIG_PATH = SCRIPT_DIR + "/conf.xml"

def is_args_valid(args):
    if len(args) < 2:
        print("サブコマンドを指定してください (ex. add_recipe)", file=sys.stderr)
        return False
    elif args[1] not in ["add_recipe", "show_recipe", "delete_recipe", "set_max_stuck", "help"]:
        print("不明なサブコマンドです: {}".format(args[1]), file=sys.stderr)
        help()
        return False
    elif args[1] == "add_recipe" and (len(args) < 5 or len(args) % 2 == 0):
        print("add_recipe の引数の書式が不正です\nadd_recipe 製作物名 素材名1 素材1の必要個数 素材名2 素材2の必要個数", file=sys.stderr)
        help("add_recipe")
        return False
    elif args[1] == "show_recipe" and len(args) not in  [3, 4]:
        print("show_recipe の引数の書式が不正です\show_recipe 見たいレシピ名 [作成個数]", file=sys.stderr)
        help("show_recipe")
        return False
    elif args[1] == "delete_recipe" and len(args) != 3:
        print("delete_recipe の引数の書式が不正です\ndelete_recipe 削除するレシピ名", file=sys.stderr)
        help("delete_recipe")
    elif args[1] == "set_max_stuck" and len(args) != 4:
        print("set_max_stuck の引数の書式が不正です\set_max_stuck 名前 スタックする個数", file=sys.stderr)
        help("set_max_stuck")
    return True

def is_config_exist():
    return os.path.isfile(CONFIG_PATH)

def create_config():
    print("MySQL サーバのユーザ名を入力")
    username = input("username: ")
    print("MySQL サーバのパスワードを入力")
    password = getpass.getpass("password: ")
    root = ET.Element("root")
    ET.SubElement(root, "username").text = username
    ET.SubElement(root, "password").text = password
    tree = ET.ElementTree(root)
    tree.write(CONFIG_PATH, encoding="UTF-8")
    return

def insert_into_objects(conn, name):
    with conn.cursor() as cursor:
        sql = "INSERT INTO objects (name) VALUES (%s)"
        cursor.execute(sql, (name))
    conn.commit()
    return

def select(conn, sql, args):
    with conn.cursor() as cursor:
        cursor.execute(sql, args)
    return cursor.fetchall()

def change(conn, sql, args):
    with conn.cursor() as cursor:
        cursor.execute(sql, args)
    conn.commit()
    return

def select_id_from_objects(conn, name):
    result = select(conn, "SELECT id FROM objects WHERE name = %s", (name))
    if result == ():
        result = None
    else:
        result = result[0]["id"]
    return result

def select_product_id_from_recipes(conn, product_id):
    result = select(conn, "SELECT product_id FROM recipes WHERE product_id = %s", (product_id))
    if result == ():
        result = None
    else:
        result = result[0]["product_id"]
    return result

def insert_into_recipes(conn, product_id, materials_id_dict):
    sql = "INSERT INTO recipes (product_id, material_id, material_required_number) VALUES " + ("(%s, %s, %s), " * (len(materials_id_dict) - 1)) + "(%s, %s, %s)"
    args = ()
    for material_id, material_required_number in materials_id_dict.items():
        args += (product_id, material_id, material_required_number)
    change(conn, sql, args)
    return

def insert_and_select_id_from_objects(conn, name):
    obj_id = select_id_from_objects(conn, name)
    if obj_id == None:
        insert_into_objects(conn, name)
        obj_id = select_id_from_objects(conn, name)
    return obj_id

def add_recipe(conn, args):
    product_name = args[2]
    try:
        materials_name_dict = dict(zip(args[3::2], [int(k) for k in args[4::2]]))
    except ValueError:
        print("個数には整数値を入力してください", file=sys.stderr)
        exit(1)
    product_id = insert_and_select_id_from_objects(conn, product_name)
    if select_product_id_from_recipes(conn, product_id) != None:
        print("そのレシピは既に登録されています\n変更する場合は削除してください", file=sys.stderr)
        exit(1)
    materials_id_dict = {insert_and_select_id_from_objects(conn, material_name): material_required_number for material_name, material_required_number in materials_name_dict.items()}
    insert_into_recipes(conn, product_id, materials_id_dict)
    return

def show_recipe(conn, args, prefix=""):
    product_name = args[2]
    if len(args) < 4:
        number_of_product = 1
    else:
        try:
            number_of_product = int(args[3])
        except ValueError:
            print("個数には整数値を入力してください", file=sys.stderr)
            exit(1)
    matches = select(conn, "SELECT product_id, matched_objects.name AS product_name, matched_objects.max_stuck, objects.name as material_name, material_required_number FROM recipes RIGHT JOIN (SELECT id, name, max_stuck FROM objects WHERE name LIKE (%s)) AS matched_objects ON recipes.product_id = matched_objects.id LEFT JOIN objects on objects.id = recipes.material_id", (product_name.replace("*", "%").replace("?", "_")))
    if len(matches) == 1 and matches[0]["product_id"] == None and prefix != "":
        print("{}{}: {}".format(prefix, matches[0]["product_name"], number_of_product), end = "")
        if matches[0]["max_stuck"] != None:
            max_stuck = matches[0]["max_stuck"]
            print(" ({} スタック、{} 列)".format(round(number_of_product / max_stuck, 2), round(number_of_product / (max_stuck * 6), 2)), end = "")
        print()
        return
    elif matches == () or [0 for match in matches if match["product_id"] != None] == []:
        print("そのレシピは登録されていません", file=sys.stderr)
        exit(1)

    matches = [match for match in matches if match["material_required_number"] != None]
    before_product_name = ""
    for match in matches:
        if before_product_name != match["product_name"]:
            if before_product_name != "":
                print()
            print("{}{}: {}".format(prefix, match["product_name"], number_of_product), end = "")
            if match["max_stuck"] != None:
                max_stuck = match["max_stuck"]
                print(" ({} スタック、{} 列)".format(round(number_of_product / max_stuck, 2), round(number_of_product / (max_stuck * 6), 2)), end = "")
            print()
        show_recipe(conn, (None, None, match["material_name"], number_of_product * match["material_required_number"]), prefix + "  ")
        before_product_name = match["product_name"]

def delete_recipe(conn, args):
    product_name = args[2]
    product_id = select_id_from_objects(conn, product_name)
    change(conn, "DELETE FROM recipes WHERE product_id = (%s)", (product_id))
    return

def set_max_stuck(conn, args):
    obj_name = args[2]
    try:
        max_stuck = int(args[3])
    except ValueError:
        print("スタックする数には整数値を入力してください", file=sys.stderr)
        exit(1)
    change(conn, "UPDATE objects SET max_stuck = (%s) WHERE name = (%s)", (max_stuck, obj_name))
    return


def help(target=""):
    if target in ["add_recipe", ""]:
        print("@general_bot add_recipe 製作物名 素材名1 素材1の必要個数 素材名2 素材2の必要個数 ...")
        print("製作物を 1 つ作るのに必要な素材とその個数を登録")
        print("ex. @general_bot add_recipe 麻酔薬 ナルコベリー 5 腐った肉 1")
        print()
    if target in ["show_recipe", ""]:
        print("@general_bot show_recipe 見たいレシピ名 [作成個数]")
        print("製作物を指定した個数作るのに必要な素材の数を表示")
        print("ex. @general_bot show_recipe 麻酔薬 100")
        print("ex. @general_bot show_recipe アルゲンタヴィスのサドル")
        print()
    if target in ["delete_recipe", ""]:
        print("@general_bot delete_recipe 削除するレシピ名")
        print("指定したレシピを削除")
        print("ex. @general_bot delete_recipe 石の天井")
        print()
    if target in ["set_max_stuck", ""]:
        print("@general_bot delete_recipe 名前 スタックする個数")
        print("対象物が 1 スタックいくつかを登録する")
        print("ex. @general_bot set_max_stuck こんがり肉 40")
        print()
    if target in ["help", ""]:
        print("@general_bot help")
        print("このメッセージを表示")
    return

def main(args):
    if not is_args_valid(args):
        exit(1)
    if not is_config_exist():
        create_config()
    config_tree = ET.parse(CONFIG_PATH)
    conn = pymysql.connect(host="localhost",
        user=config_tree.getroot().find("username").text,
        password=config_tree.getroot().find("password").text,
        db="ARK",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor)
    try:
        if args[1] == "add_recipe":
            add_recipe(conn, args)
        elif args[1] == "show_recipe":
            show_recipe(conn, args)
        elif args[1] == "delete_recipe":
            delete_recipe(conn, args)
        elif args[1] == "set_max_stuck":
            set_max_stuck(conn, args)
        elif args[1] == "help":
            if len(args) < 3:
                help()
            else:
                help(args[2])
    finally:
        conn.close()
    return

if __name__ == "__main__":
    main(sys.argv)
