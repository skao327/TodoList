import tkinter as tk
from tkinter import messagebox
import sqlite3
root=tk.TK()

#db세팅
comm=sqlite3.connect('todolist.db') #todolist라는 이름의 파일로 db연결결
cursor = conn.cursor() #sql 문장을 실행하기 위해 커서 객체 생성
cursor.execute('''                             
CREATE TABLE IF NOT EXISTS todolists (         
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task TEXT NOT NULL,
    completed INTEGER NOT NULL DEFAULT 0
)
''')
conn.commit() #변경 사항을 db에 저장장

#함수 정의
def load_tasks(): #할 일 불러오기기(리스트박스를 초기화한 후 db에서 할 일 목록을 가져와 리스트박스에 표시(완료 항목엔 [완료]를 붙임))
    task_listbox.delete(0, tk.END)
    cursor.execute("SELECT id, task, completed FROM todolist")
    for row in cursor.fetchall():
        text = row[1] + (" [완료]" if row[2] else "")
        task_listbox.insert(tk.END, text)

def add_task():  #할 일 추가(텍스트 입력창에서 할 일을 가져와 db에 추가, 추가 후 입력창 비우고 목록을 새로고침)
    task = entry.get()
    if task:
        cursor.execute("INSERT INTO todos (task) VALUES (?)", (task,))
        conn.commit()
        entry.delete(0, tk.END)
        load_tasks()

def delete_task(): #할 일 삭제(선택된 리스트 항목의 텍스트를 가져와 db에서 삭제, [완료]는 저장된 값이 아니므로 제거 후 비교, 삭제 후 새로고침)
    selected = task_listbox.curselection()
    if selected:
        index = selected[0]
        task_text = task_listbox.get(index).replace(" [완료]", "")
        cursor.execute("DELETE FROM todos WHERE task=?", (task_text,))
        conn.commit()
        load_tasks()

def toggle_complete(): #완료 처리 토글(리스트박스에서 선택한 항목의 완료 여부를 반전시킴, 완료료된 상태면 미완료로, 미완료 상태면 완료로 바꿈, 업테이트 후 새로고침/)
    selected = task_listbox.curselection()
    if selected:
        index = selected[0]
        task_text = task_listbox.get(index).replace(" [완료]", "")
        cursor.execute("SELECT id, completed FROM todos WHERE task=?", (task_text,))
        row = cursor.fetchone()
        if row:
            new_status = 0 if row[1] else 1
            cursor.execute("UPDATE todos SET completed=? WHERE id=?", (new_status, row[0]))
            conn.commit()
            load_tasks()

#gui 구성
root.title("To-do List") #맨 위에 제목("To-do List")
root.geometry("400x500") #사이즈
task_entry=tk.entry(root,width=30) #텍스트 입력창 
task_entry.pack(pady=10)

add_button=tk.Button(root,text="추가",width=10)
add_button.pack(pady=5)

task_listbox=tk.Listbox(root,width=40,height=15)
task_listbox.pack(pady=10)

delete_button=tk.Button(root,text="삭제",width=10)
delete_button.pack(pady=5)

complete_button=tk.Button(root,text="완료",width=10)
complete_button.pack(pady=5)

load_tasgs()

root.mainloop()

conn.close()