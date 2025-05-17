import tkinter as tk
from tkinter import messagebox
import sqlite3

class Todo:

    UNCHECKED = "☐ "
    CHECKED = "☑ "
    
    def __init__(self, root):
        self.root = root
        root.title("To-do List") #맨 위에 제목("To-do List")
        root.geometry("400x500") #사이즈

        # db세팅 (주석 대신 실제 동작 코드로)
        self.conn = sqlite3.connect('todolist.db') #todolist라는 이름의 파일로 db연결
        self.cursor = self.conn.cursor() #sql 문장을 실행하기 위해 커서 객체 생성
        self.cursor.execute('''                             
        CREATE TABLE IF NOT EXISTS todolists (         
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 0
        )
        ''')
        self.conn.commit() #변경 사항을 db에 저장

        self.listbox_task_ids = []

        # [추가] 삭제된 항목 복구용 스택
        self.deleted_item_stack = []

        self.setup_gui()
        self.display_tasks()
        root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_gui(self):
        self.task_entry=tk.Entry(self.root, width=30) #텍스트 입력창 
        self.task_entry.pack(pady=10)
        self.task_entry.bind("<Return>", self.add_task)

        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=5)

        self.add_button=tk.Button(button_frame, text="추가", width=10, command=self.add_task)
        self.add_button.pack(side=tk.LEFT, padx=5)

        # [추가] 삭제 버튼
        self.delete_button = tk.Button(button_frame, text="삭제", width=10, command=self.delete_task)
        self.delete_button.pack(side=tk.LEFT, padx=5)

        # [추가] 복구(undo) 버튼
        self.undo_button = tk.Button(button_frame, text="복구", width=10, command=self.undo_delete)
        self.undo_button.pack(side=tk.LEFT, padx=5)

        list_frame = tk.Frame(self.root)
        list_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        self.task_listbox=tk.Listbox(self.root, width=40, height=15, selectmode=tk.SINGLE)
        self.task_listbox.bind('<<ListboxSelect>>', self.toggle_complete)

        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=self.task_listbox.yview)
        self.task_listbox.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.task_listbox.pack(side=tk.LEFT, fill="both", expand=True)


    def display_tasks(self): #할 일 불러오기(리스트박스를 초기화한 후 db에서 할 일 목록을 가져와 리스트박스에 표시(완료 항목엔 [완료]를 붙임))
        self.task_listbox.delete(0, tk.END)
        self.listbox_task_ids.clear()
        listbox_idx = 0
        try:
            self.cursor.execute("SELECT id, task, completed FROM todolists ORDER BY completed ASC, id ASC")
            for row in self.cursor.fetchall():
                task_id, task_text, completed_status = row
                prefix = self.CHECKED if completed_status else self.UNCHECKED
                display_text = prefix + task_text
                self.task_listbox.insert(tk.END, display_text)
                self.listbox_task_ids.append(task_id)

                if completed_status:
                    self.task_listbox.itemconfig(tk.END, {'fg': 'gray'})
                else:
                    self.task_listbox.itemconfig(tk.END, {'fg': 'black'})
        except sqlite3.Error as e:
            messagebox.showerror("DB 오류", f"할 일 목록을 불러오는 중 오류 발생: {e}")

    def add_task(self, event=None):  #할 일 추가(텍스트 입력창에서 할 일을 가져와 db에 추가, 추가 후 입력창 비우고 목록을 새로고침)
        task = self.task_entry.get()
        if task:
            try:
                self.cursor.execute("INSERT INTO todolists (task) VALUES (?)", (task,))
                self.conn.commit()
                print(f"할 일 추가: {task}")
                self.task_entry.delete(0, tk.END)
                self.display_tasks()
            except sqlite3.Error as e:
                messagebox.showerror("DB 오류", f"할 일 추가 중 오류 발생: {e}")
        else:
            messagebox.showwarning("경고", "할 일을 입력해주세요.")

    # [수정] delete_task를 클래스 메서드로 변경 및 올바르게 구현
    def delete_task(self):
        selected = self.task_listbox.curselection()
        if selected:
            index = selected[0]
            task_id = self.listbox_task_ids[index]
            try:
                # 삭제 전 항목 임시저장 (복구용)
                self.cursor.execute("SELECT id, task, completed FROM todolists WHERE id=?", (task_id,))
                deleted_row = self.cursor.fetchone()
                if deleted_row:
                    self.deleted_item_stack.append(deleted_row)
                    self.cursor.execute("DELETE FROM todolists WHERE id=?", (task_id,))
                    self.conn.commit()
                    self.display_tasks()
            except sqlite3.Error as e:
                messagebox.showerror("DB 오류", f"할 일 삭제 중 오류 발생: {e}")
        else:
            messagebox.showwarning("경고", "삭제할 항목을 선택해주세요.")

    # [추가] 복구(undo) 메서드
    def undo_delete(self):
        if self.deleted_item_stack:
            last_deleted = self.deleted_item_stack.pop()
            _, task, completed = last_deleted
            try:
                self.cursor.execute("INSERT INTO todolists (task, completed) VALUES (?, ?)", (task, completed))
                self.conn.commit()
                self.display_tasks()
            except sqlite3.Error as e:
                messagebox.showerror("DB 오류", f"삭제 복구 중 오류 발생: {e}")
        else:
            messagebox.showinfo("안내", "복구할 항목이 없습니다.")

    def toggle_complete(self, event=None): #완료 처리 토글(리스트박스에서 선택한 항목의 완료 여부를 반전시킴, 완료된 상태면 미완료로, 미완료 상태면 완료로 바꿈, 업테이트 후 새로고침)
        selected = self.task_listbox.curselection()
        if not selected:
            return
        
        selected_listbox_index = selected[0]

        taskID_toTOGGLE = self.listbox_task_ids[selected_listbox_index]

        try:
            self.cursor.execute("SELECT id, completed FROM todolists WHERE id=?", (taskID_toTOGGLE,))
            result = self.cursor.fetchone()
            if result:
                current_status = result[1]
                new_status = 0 if current_status else 1
                self.cursor.execute("UPDATE todolists SET completed=? WHERE id=?", (new_status, taskID_toTOGGLE))
                self.conn.commit()
                self.display_tasks()
            else:
                messagebox.showinfo("오류", "완료 처리할 항목을 선택해주세요.")
        except sqlite3.Error as e:
            messagebox.showerror("DB 오류", f"완료 상태 변경 중 오류 발생:{e}")

    def on_closing(self):
        if self.conn:
            self.conn.close()
            print("DB 연결이 종료되었습니다.")
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = Todo(root)
    root.mainloop()

#gui 구성
"""
delete_button=tk.Button(root,text="삭제",width=10)
delete_button.pack(pady=5)

complete_button=tk.Button(root,text="완료",width=10, command=toggle_complete)
complete_button.pack(pady=5)

load_tasks()

root.mainloop()

conn.close()
"""
