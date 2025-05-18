import tkinter as tk
import mysql.connector
from tkinter import messagebox

class Todo:

    UNCHECKED = "☐ "
    CHECKED = "☑ "
    
    def __init__(self, root):
        self.root = root
        root.title("To-do List") #맨 위에 제목("To-do List")
        root.geometry("400x550") #사이즈 (버튼 추가로 살짝 늘림)

        #db세팅
        self.conn = mysql.connector.connect(
            host="127.0.0.1",
            user="todo_user",
            password="mypass123",
            database="todo_db"
        )

        self.cursor = self.conn.cursor()
        self.cursor.execute("SELECT DATABASE();")
        print(self.cursor.fetchone())

        # 테이블이 없으면 자동 생성 + sort_order 컬럼 추가
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS todolists (
                id INT AUTO_INCREMENT PRIMARY KEY,
                task VARCHAR(255) NOT NULL,
                completed TINYINT(1) NOT NULL DEFAULT 0,
                sort_order INT NOT NULL DEFAULT 0
            )
        """)
        # 기존 테이블에 컬럼 없을 때 자동 추가 (이미 있으면 무시)
        try:
            self.cursor.execute("ALTER TABLE todolists ADD COLUMN sort_order INT NOT NULL DEFAULT 0")
            self.conn.commit()
        except Exception:
            pass

        self.listbox_task_ids = []

        # 삭제된 항목 복구용 스택
        self.deleted_item_stack = []

        self.setup_gui()
        self._ensure_sort_order() # 기존 DB의 sort_order를 정렬 상태로 초기화
        self.display_tasks()
        root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_gui(self):
        self.task_entry=tk.Entry(self.root, width=30) #텍스트 입력창 
        self.task_entry.pack(pady=10)
        self.task_entry.bind("<Return>", self.add_task)

        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=5)

        self.add_button = tk.Button(button_frame, text="추가", width=8, command=self.add_task)
        self.add_button.pack(side=tk.LEFT, padx=2)

        # 삭제/복구
        self.delete_button = tk.Button(button_frame, text="삭제", width=8, command=self.delete_task)
        self.delete_button.pack(side=tk.LEFT, padx=2)
        self.undo_button = tk.Button(button_frame, text="복구", width=8, command=self.undo_delete)
        self.undo_button.pack(side=tk.LEFT, padx=2)

        # 순서 이동 버튼
        self.up_button = tk.Button(button_frame, text="↑ 위로", width=8, command=self.move_up)
        self.up_button.pack(side=tk.LEFT, padx=2)
        self.down_button = tk.Button(button_frame, text="↓ 아래로", width=8, command=self.move_down)
        self.down_button.pack(side=tk.LEFT, padx=2)

        list_frame = tk.Frame(self.root)
        list_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        # 다중 선택 지원
        self.task_listbox=tk.Listbox(self.root, width=40, height=15, selectmode=tk.EXTENDED)
        self.task_listbox.bind('<Double-Button-1>', self.toggle_complete)

        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=self.task_listbox.yview)
        self.task_listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.task_listbox.pack(side=tk.LEFT, fill="both", expand=True)

    def display_tasks(self): #할 일 불러오기(정렬순서→아이디 오름차순)
        self.task_listbox.delete(0, tk.END)
        self.listbox_task_ids.clear()
        try:
            self.cursor.execute("SELECT id, task, completed FROM todolists ORDER BY sort_order ASC, id ASC")
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
        except mysql.connector.Error as e:
            messagebox.showerror("DB 오류", f"할 일 목록을 불러오는 중 오류 발생: {e}")

    def add_task(self, event=None):  #할 일 추가(텍스트 입력창에서 할 일을 가져와 db에 추가, 추가 후 입력창 비우고 목록을 새로고침)
        task = self.task_entry.get()
        if task:
            try:
                # 가장 큰 sort_order 뒤에 추가
                self.cursor.execute("SELECT IFNULL(MAX(sort_order), 0) FROM todolists")
                max_order = self.cursor.fetchone()[0]
                self.cursor.execute("INSERT INTO todolists (task, sort_order) VALUES (%s, %s)", (task, max_order + 1))
                self.conn.commit()
                print(f"할 일 추가: {task}")
                self.task_entry.delete(0, tk.END)
                self.display_tasks()
            except mysql.connector.Error as e:
                messagebox.showerror("DB 오류", f"할 일 추가 중 오류 발생: {e}")
        else:
            messagebox.showwarning("경고", "할 일을 입력해주세요.")

    def delete_task(self): #다중 선택 삭제(복구 스택에 저장)
        selected_indices = self.task_listbox.curselection()
        if selected_indices:
            for index in sorted(selected_indices, reverse=True):
                task_id = self.listbox_task_ids[index]
                try:
                    self.cursor.execute("SELECT id, task, completed, sort_order FROM todolists WHERE id=%s", (task_id,))
                    deleted_row = self.cursor.fetchone()
                    if deleted_row:
                        self.deleted_item_stack.append(deleted_row)
                        self.cursor.execute("DELETE FROM todolists WHERE id=%s", (task_id,))
                        self.conn.commit()
                except mysql.connector.Error as e:
                    messagebox.showerror("DB 오류", f"할 일 삭제 중 오류 발생: {e}")
            self._reorder_sort_orders()
            self.display_tasks()
        else:
            messagebox.showwarning("경고", "삭제할 항목을 선택해주세요.")

    def undo_delete(self):
        if self.deleted_item_stack:
            last_deleted = self.deleted_item_stack.pop()
            _, task, completed, _ = last_deleted
            try:
                self.cursor.execute("SELECT IFNULL(MAX(sort_order), 0) FROM todolists")
                max_order = self.cursor.fetchone()[0]
                self.cursor.execute("INSERT INTO todolists (task, completed, sort_order) VALUES (%s, %s, %s)", (task, completed, max_order + 1))
                self.conn.commit()
                self.display_tasks()
            except mysql.connector.Error as e:
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
            self.cursor.execute("SELECT id, completed FROM todolists WHERE id=%s", (taskID_toTOGGLE,))
            result = self.cursor.fetchone()
            if result:
                current_status = result[1]
                new_status = 0 if current_status else 1
                self.cursor.execute("UPDATE todolists SET completed=%s WHERE id=%s", (new_status, taskID_toTOGGLE))
                self.conn.commit()
                self.display_tasks()
            else:
                messagebox.showinfo("오류", "완료 처리할 항목을 선택해주세요.")
        except mysql.connector.Error as e:
            messagebox.showerror("DB 오류", f"완료 상태 변경 중 오류 발생:{e}")

    # [추가] 순서 이동 함수
    def move_up(self):
        selected = self.task_listbox.curselection()
        if not selected or len(selected) != 1:
            return
        idx = selected[0]
        if idx == 0:
            return
        current_id = self.listbox_task_ids[idx]
        above_id = self.listbox_task_ids[idx - 1]
        # sort_order 값 서로 교환
        self.cursor.execute("SELECT sort_order FROM todolists WHERE id=%s", (current_id,))
        order1 = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT sort_order FROM todolists WHERE id=%s", (above_id,))
        order2 = self.cursor.fetchone()[0]
        self.cursor.execute("UPDATE todolists SET sort_order=%s WHERE id=%s", (order2, current_id))
        self.cursor.execute("UPDATE todolists SET sort_order=%s WHERE id=%s", (order1, above_id))
        self.conn.commit()
        self.display_tasks()
        self.task_listbox.selection_clear(0, tk.END)
        self.task_listbox.selection_set(idx - 1)

    def move_down(self):
        selected = self.task_listbox.curselection()
        if not selected or len(selected) != 1:
            return
        idx = selected[0]
        if idx == len(self.listbox_task_ids) - 1:
            return
        current_id = self.listbox_task_ids[idx]
        below_id = self.listbox_task_ids[idx + 1]
        self.cursor.execute("SELECT sort_order FROM todolists WHERE id=%s", (current_id,))
        order1 = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT sort_order FROM todolists WHERE id=%s", (below_id,))
        order2 = self.cursor.fetchone()[0]
        self.cursor.execute("UPDATE todolists SET sort_order=%s WHERE id=%s", (order2, current_id))
        self.cursor.execute("UPDATE todolists SET sort_order=%s WHERE id=%s", (order1, below_id))
        self.conn.commit()
        self.display_tasks()
        self.task_listbox.selection_clear(0, tk.END)
        self.task_listbox.selection_set(idx + 1)

    # 삭제 후 sort_order 재정렬
    def _reorder_sort_orders(self):
        self.cursor.execute("SELECT id FROM todolists ORDER BY sort_order ASC, id ASC")
        rows = self.cursor.fetchall()
        for i, (row_id,) in enumerate(rows):
            self.cursor.execute("UPDATE todolists SET sort_order=%s WHERE id=%s", (i, row_id))
        self.conn.commit()

    # 기존 DB에 sort_order가 0만 있을 때 다시 정렬
    def _ensure_sort_order(self):
        self.cursor.execute("SELECT COUNT(*), SUM(sort_order) FROM todolists")
        count, total = self.cursor.fetchone()
        if count > 1 and (total == 0 or total is None):
            self._reorder_sort_orders()

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
