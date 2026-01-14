# -*- coding: utf-8 -*-
import os
import random
import json
import sys


def get_current_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.abspath(__file__))


def get_random_word():
    current_path = get_current_path()
    words_dir = os.path.join(current_path, "books")    
    if not os.path.exists(words_dir):
        raise FileNotFoundError(
            f"未找到单词目录\n"
            f"路径：{words_dir}\n"
            f"请确保程序目录下有'books'文件夹并包含单词JSON文件"
        )
    
    json_files = [f for f in os.listdir(words_dir) if f.lower().endswith(".json")]
    if not json_files:
        raise FileNotFoundError(f"books目录中无JSON文件：{words_dir}")

    selected_file = random.choice(json_files)
    file_path = os.path.join(words_dir, selected_file)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            word_data = json.load(f)
    except json.JSONDecodeError:
        raise ValueError(f"JSON格式错误：{selected_file}")
    except Exception as e:
        raise IOError(f"读取文件失败：{str(e)}")

    result = {
        "word": word_data.get("headWord", "未知单词"),
        "word_rank": str(word_data.get("wordRank", "未知")),
        "pos": [],
        "definition": [],
        "example": "无例句",
        "raw_sentences": []
    }
    
    trans_info = word_data.get("content", {}).get("word", {}).get("content", {}).get("trans", [])
    for item in trans_info:
        pos = item.get("pos", "未知词性")
        if pos not in result["pos"]:
            result["pos"].append(pos)
        
        cn_def = item.get("tranCn", "").strip()
        en_def = item.get("tranOther", "").strip()
        full_def = f"{pos}：{cn_def}"
        if en_def:
            full_def += f"\n{en_def}"
        result["definition"].append(full_def)
    
    result["pos"] = ", ".join(result["pos"]) if result["pos"] else "无词性信息"
    result["definition"] = "\n\n".join(result["definition"]) if result["definition"] else "无释义信息"
    
    sentences = word_data.get("content", {}).get("word", {}).get("content", {}).get("sentence", {}).get("sentences", [])
    if sentences:
        result["raw_sentences"] = sentences
        selected_sentence = random.choice(sentences)
        result["example"] = f"{selected_sentence.get('sContent', '')}\n{selected_sentence.get('sCn', '')}"
    
    return result


def get_word_by_rank(target_rank):
    """根据wordRank查找单词信息（用于默写）"""
    current_path = get_current_path()
    words_dir = os.path.join(current_path, "books")
    
    if not os.path.exists(words_dir):
        raise FileNotFoundError(f"未找到books目录：{words_dir}")
    
    json_files = [f for f in os.listdir(words_dir) if f.lower().endswith(".json")]
    if not json_files:
        raise FileNotFoundError(f"books目录中无JSON文件：{words_dir}")
    
    for file in json_files:
        file_path = os.path.join(words_dir, file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                word_data = json.load(f)
        except:
            continue
        
        if str(word_data.get("wordRank", "")) == target_rank:
            return {
                "word": word_data.get("headWord", "未知单词"),
                "raw_sentences": word_data.get("content", {}).get("word", {}).get("content", {}).get("sentence", {}).get("sentences", [])
            }
    
    raise ValueError(f"未找到wordRank为 {target_rank} 的单词")
