import fnmatch
import os
import sys

from tkinter import StringVar, BooleanVar
from tkinter.ttk import Checkbutton

from idlelib.searchbase import SearchDialogBase
from idlelib import searchengine

# Importing OutputWindow here fails due to import loop
# EditorWindow -> GrepDialop -> OutputWindow -> EditorWindow

def grep(text, io=None, flist=None):
    root = text._root()
    engine = searchengine.get(root)
    if not hasattr(engine, "_grepdialog"):
        engine._grepdialog = GrepDialog(root, engine, flist)
    dialog = engine._grepdialog
    searchphrase = text.get("sel.first", "sel.last")
    dialog.open(text, searchphrase, io)

class GrepDialog(SearchDialogBase):

    title = "文件内容查找对话框"
    icon = "Grep"
    needwrapbutton = 0

    def __init__(self, root, engine, flist):
        SearchDialogBase.__init__(self, root, engine)
        self.flist = flist
        self.globvar = StringVar(root)
        self.recvar = BooleanVar(root)

    def open(self, text, searchphrase, io=None):
        SearchDialogBase.open(self, text, searchphrase)
        if io:
            path = io.filename or ""
        else:
            path = ""
        dir, base = os.path.split(path)
        head, tail = os.path.splitext(base)
        if not tail:
            tail = ".py"
        self.globvar.set(os.path.join(dir, "*" + tail))

    def create_entries(self):
        SearchDialogBase.create_entries(self)
        self.globent = self.make_entry("文件类型:", self.globvar)[0]

    def create_other_buttons(self):
        btn = Checkbutton(
                self.make_frame()[0], variable=self.recvar,
                text="是否包含子目录")
        btn.pack(side="top", fill="both")

    def create_command_buttons(self):
        SearchDialogBase.create_command_buttons(self)
        self.make_button("文件中查找", self.default_command, 1)

    def default_command(self, event=None):
        prog = self.engine.getprog()
        if not prog:
            return
        path = self.globvar.get()
        if not path:
            self.top.bell()
            return
        from idlelib.outwin import OutputWindow  # leave here!
        save = sys.stdout
        try:
            sys.stdout = OutputWindow(self.flist)
            self.grep_it(prog, path)
        finally:
            sys.stdout = save

    def grep_it(self, prog, path):
        dir, base = os.path.split(path)
        list = self.findfiles(dir, base, self.recvar.get())
        list.sort()
        self.close()
        pat = self.engine.getpat()
        print("查找 %r 在 %s ..." % (pat, path))
        hits = 0
        try:
            for fn in list:
                try:
                    with open(fn, errors='replace') as f:
                        for lineno, line in enumerate(f, 1):
                            if line[-1:] == '\n':
                                line = line[:-1]
                            if prog.search(line):
                                sys.stdout.write("%s: %s: %s\n" %
                                                 (fn, lineno, line))
                                hits += 1
                except OSError as msg:
                    print(msg)
            print(("查找结果: %s\n"
                  "(跳转: 右击打开目标位置.)"
                  % hits) if hits else "没有发现匹配内容.")
        except AttributeError:
            # Tk window has been closed, OutputWindow.text = None,
            # so in OW.write, OW.text.insert fails.
            pass

    def findfiles(self, dir, base, rec):
        try:
            names = os.listdir(dir or os.curdir)
        except OSError as msg:
            print(msg)
            return []
        list = []
        subdirs = []
        for name in names:
            fn = os.path.join(dir, name)
            if os.path.isdir(fn):
                subdirs.append(fn)
            else:
                if fnmatch.fnmatch(name, base):
                    list.append(fn)
        if rec:
            for subdir in subdirs:
                list.extend(self.findfiles(subdir, base, rec))
        return list

    def close(self, event=None):
        if self.top:
            self.top.grab_release()
            self.top.withdraw()


def _grep_dialog(parent):  # htest #
    from tkinter import Toplevel, Text, SEL, END
    from tkinter.ttk import Button
    from idlelib.pyshell import PyShellFileList
    top = Toplevel(parent)
    top.title("Test GrepDialog")
    x, y = map(int, parent.geometry().split('+')[1:])
    top.geometry("+%d+%d" % (x, y + 175))

    flist = PyShellFileList(top)
    text = Text(top, height=5)
    text.pack()

    def show_grep_dialog():
        text.tag_add(SEL, "1.0", END)
        grep(text, flist=flist)
        text.tag_remove(SEL, "1.0", END)

    button = Button(top, text="Show GrepDialog", command=show_grep_dialog)
    button.pack()

if __name__ == "__main__":
    import unittest
    unittest.main('idlelib.idle_test.test_grep', verbosity=2, exit=False)

    from idlelib.idle_test.htest import run
    run(_grep_dialog)
