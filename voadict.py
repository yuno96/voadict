#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

Prog = 'VOAdict'
Version = '0.1.0'
import sys, os
import wave, pyaudio
import threading
import time
import bs4
import requests
#from tkinter import *
#from tkinter.colorchooser import askcolor
#from guimaker import *

import tkinter as tk
from tkinter.filedialog import Open, SaveAs
from tkinter.messagebox import showinfo, showerror, askyesno
from tkinter.simpledialog import askstring, askinteger

try:
    import textConfig
    configs = textConfig.__dict__
except:
    configs = {}

helpText = """VOAdict version %s
August 29, 2014

1. Introduction
---------------
This software is to transcribe audio 
file, which is especially useful for 
foreign language learnner. Every 
audio control like Play, backward, 
and forward is handled by the 
keyboard.

2. How to use
---------------
a. Open VOA
    File --> Open VOA
b. Start audio play
    Mouse click '>II' button
c. Forward or backward play
    Mouse click '<<' or '>>'

3. Keyboard shortcut
---------------
a. 'Control-Space': Play Audio
b. 'Control-[': Backward and Play
c. 'Control-]': Forward and Play

4. Information
If you have any suggession or find 
any bugs, please email me to
yhjeon@knou.ac.kr
"""

FontScale = 0
if sys.platform[:3] != 'win':
    FontScale = 3

class View():
	def __init__(self, master, menuList, btnAttr, goPos):
		#print ("GuiMaker __init__: self="+self.__class__.__name__)
		self.frame = tk.Frame(master)
		self.frame.pack(expand=tk.YES, fill=tk.BOTH)

		#Frame.__init__(self, parent)
		#self.pack(expand=YES, fill=BOTH)
		#self.start()
		self.makeMenuBar(master, menuList)
		self.scaleVar = tk.IntVar()
		self.scale = self.makeToolBar(master, btnAttr, goPos, self.scaleVar)
		self.text = self.makeText(master)

	def makeMenuBar(self, master, menuList):
		menubar = tk.Frame(master, bd=2)
		menubar.pack(side=tk.TOP, fill=tk.X)

		for (name, key, items) in menuList:
			mbutton = tk.Menubutton(menubar, text=name, underline=key)
			mbutton.pack(side=tk.LEFT)
			pulldown = tk.Menu(mbutton)
			self.addMenuItems(pulldown, items)
			mbutton.config(menu=pulldown)

		def helpfunc():
			showinfo('About '+Prog, helpText % Version)

		tk.Button(menubar, text='Help', cursor='gumby', relief=tk.FLAT,
				command=helpfunc).pack(side=tk.RIGHT)

	def addMenuItems(self, menu, items):
		for item in items:
			if item == 'separator':
				menu.add_separator({})
			elif type(item) == list:
				for num in item:
					menu.entryconfig(num, state=tk.DISABLED)
			elif type(item[2]) != list:
				menu.add_command(label = item[0],
						underline = item[1],
						command = item[2])
			else:
				pullover = Menu(menu)
				self.addMenuItems(pullover, item[2])
				menu.add_cascade(label = item[0],
						underline = item[1],
						menu = pullover)
	
	def makeToolBar(self, master, btnAttr, goPos, scaleVar):
		toolbar = tk.Frame(master, cursor='hand2', 
					relief=tk.FLAT, bd=2)
		toolbar.pack(side=tk.TOP, fill=tk.X)
		
		#(display, action, where) = btnAttr[0]
		#self.BTN_PNS = tk.Button(toolbar, text=display, command=action)
		#self.BTN_PNS.pack(where)
		#for (display, action, where) in btnAttr[1:]:
		#	tk.Button(toolbar, text=display, command=action).pack(where)
		for (display, action, where) in btnAttr:
			tk.Button(toolbar, text=display, command=action).pack(where)
		scale = tk.Scale(toolbar, orient='horizontal', showvalue=tk.NO,
				command=goPos, variable=self.scaleVar)
		scale.pack(fill=tk.X)
		#self.wavePlayer = WavePlayer(master)
		#self.WavePlayer.pack(fill=tk.X)
		return scale

	def makeText(self, master):
		name = tk.Label(master, relief=tk.SUNKEN)
		name.pack(side=tk.BOTTOM, fill=tk.X)

		vbar = tk.Scrollbar(master)
		text = tk.Text(master, padx=5, wrap=tk.CHAR)
		text.config(undo=1, autoseparators=1)          # 2.0, default is 0, 1
		vbar.pack(side=tk.RIGHT, fill=tk.Y)
		text.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)
		text.config(yscrollcommand=vbar.set)
		vbar.config(command=text.yview)
		return text

	def getAllText(self):
		return self.text.get('1.0', tk.END+'-1c')

	def setAllText(self, text):
		self.text.delete('1.0', tk.END)
		self.text.insert(tk.END, text)
		self.text.mark_set(tk.INSERT, '1.0')
		self.text.see(tk.INSERT)


class ModelWavePlayer(threading.Thread):
	CHUNK = 1024

	def __init__(self, view):
		#print ("__init__: self="+self.__class__.__name__)
		self.view = view
		self.lock = threading.RLock()
		self.evt = threading.Event()
		self.mutex = threading.Lock()
		self.filepath = None
		self.filesz = 0
		self.pause = True
		self.loop = False
		self.wf = self.stream = self.player = None
		self.SEC = self.curPos = self.nframe = 0
		self.rePos = -1

	def isOpened(self):
		return True if self.filepath else False

	def isPaused(self):
		return self.pause

	def togglePause(self):
		if not self.loop:
			return

		if self.pause:
			self.evt.set()
			self.evt.clear()

		self.pause = not self.pause

	def onOpen(self, filepath=None):
		if self.isOpened():
			self.onClose()

		self.loop = True
		self.filepath = filepath
		self.filesz = os.path.getsize(filepath)
		try:
			wf = wave.open(filepath, 'rb')
		except:
			self.filepath = None
			print('Error wave open')
			return False

		sampwidth = wf.getsampwidth()
		chnum = wf.getnchannels()
		frate = wf.getframerate()
		self.nframe = wf.getnframes()
		div = (chnum*sampwidth*frate)
		self.SEC = frate
		#print ('***' + str(wf.getparams()))

		p = pyaudio.PyAudio()
		self.stream = p.open(format=p.get_format_from_width(sampwidth),
			channels=chnum, rate=frate, output=True)
		self.wf = wf
		self.player = p
		self.pause = True
		threading.Thread.__init__(self)
		self.start()

		self.view.scale.config(from_=0)
		self.view.scale.config(to=(self.nframe/frate))
		self.view.scale.config(resolution=1)
		self.view.scaleVar.set(0)
		return True

	def onClose(self):
		if not self.isOpened():
			return

		self.loop = False
		self.pause = False
		self.evt.set()
		self.evt.clear()
		if self.isAlive():
			self.join()

		if self.wf:
			self.stream.close()
			self.player.terminate()
			self.wf.close()
			self.wf = None
			self.stream = None
			self.player = None

	def goPos(self, flag, value):
		#print ('WavePlayer onGoPos: %d'%value)
		if not self.isOpened():
			self.scaleVar.set(0)
			return

		self.mutex.acquire()
		try:
			if flag == 0:
				self.rePos = self.curPos + (self.SEC*2*value)
			else:
				self.rePos = value*self.SEC 

			if self.rePos < 0:
				self.rePos = 0
			elif self.rePos > self.nframe:
				self.rePos = self.nframe
		finally:
			self.mutex.release()

	def run(self):
		curIdx = preIdx = 0

		while self.loop:
			if self.pause:
				self.evt.wait()
				continue

			self.mutex.acquire()
			try: 
				if self.rePos != -1:
					self.wf.setpos(self.rePos)
					self.rePos = -1
			finally:
				self.mutex.release()

			data = self.wf.readframes(self.CHUNK)
			if data == '':
				self.wf.rewind()
				data = self.wf.readframes(self.CHUNK)

			self.mutex.acquire()
			try:
				self.curPos = self.wf.tell()
			finally:
				self.mutex.release()

			self.stream.write(data)

			curIdx = int(self.curPos/self.SEC)
			if preIdx != curIdx:
				self.view.scaleVar.set(curIdx)
				preIdx = curIdx

class Controller():
	startfiledir = '.'

	ftypes = [('All files',     '*'), 
			('Text files',   '.txt'), 
			('Python files', '.py')] 

	def __init__(self, noteName):
		menuList = [
			('File', 0,  # label, shortcut, callback
				[('Open Note...', 0, self.onOpenNote),   
				('Save', 0, self.onSave),
				('Save As...', 5, self.onSaveAs),
				('New', 0, self.onNew),
				'separator',
				('Open VOA', 0, self.onOpenVOA),
				('Open Audio', 0, self.onOpenAudio),
				'separator',
				('Quit...', 0, self.onQuit)]),
			('Edit', 0, 
				[('Undo', 0, self.onUndo),
				('Redo', 0, self.onRedo),
				'separator',
				('Cut', 0, self.onCut),
				('Copy', 1, self.onCopy),
				('Paste', 0, self.onPaste),
				'separator',
				('Delete', 0, self.onDelete),
				('Select All', 0, self.onSelectAll)]),
			('Search', 0,
				[('Goto...', 0, self.onGoto), 
				('Find...', 0, self.onFind),
				('Refind', 0, self.onRefind),
				('Change...',  0, self.onChange)])
		]

		btnAttr = [('>II', self.onPlayOrStop, {'side': tk.LEFT}),
				('<<', self.onReplay, {'side': tk.LEFT}),
				('>>', self.onFwplay, {'side': tk.LEFT})]

		self.root = tk.Tk()
		self.noteName = noteName
		self.view = View(self.root, menuList, btnAttr, self.goPos)
		self.model = ModelWavePlayer(self.view)

		self.root.title(Prog+' '+Version)
		self.root.iconname(Prog)
		self.root.protocol('WM_DELETE_WINDOW', self.onQuit) 


		self.keyList = [('<Control-;>', self.keyPlayOrStop),
				('<Control-bracketleft>', self.keyReplay),
				('<Control-bracketright>', self.keyFwplay)]
		for keyStr, act in self.keyList:
			self.root.bind(keyStr, act)

	def keyPlayOrStop(self, evt):
		self.onPlayOrStop()

	def onReplay(self):
		self.model.goPos(0, -2)

	def onFwplay(self):
		self.model.goPos(0, +2)

	def keyReplay(self, evt):
		self.onReplay()

	def keyFwplay(self, evt):
		self.onFwplay()
		
	def goPos(self, value):
		self.model.goPos(1, int(value))

	def my_askopenfilename(self):
		self.openDialog = Open(initialdir=self.startfiledir,
				filetypes=self.ftypes)
		return self.openDialog.show()

	def onOpenNote(self):
		fname = self.noteName
		if not fname:
			fname = self.my_askopenfilename()
			if not fname or not os.path.isfile(fname):
				showerror(Prog, 'Cannot open file '+fname)
				return
		
		contents = ''
		with open(fname, 'rb') as f:
			contents = f.read()

		contents = contents.replace(b'\r\n', b'\n')
		self.view.setAllText(contents)
		self.currfile = fname
		self.view.text.edit_reset()
		self.view.text.edit_modified(0)

	def onSave(self):
		#print('-->'+self.currfile)
		if self.currfile:
			self.onSaveAs(self.currfile)

	def onSaveAs(self, forcefile=None):
		fname = forcefile or self.my_asksaveasfname()
		if not fname:
			return

		try:
			with open(fname, 'w') as f:
				f.write(self.view.getAllText())
		except:
			showerror(Prog, 'cannot write the file ' + fname)
		else:
			self.currfile = fname
			self.view.text.edit_modified(0)

	def clearAllText(self):
		self.view.text.delete('1.0', END)

	def onNew(self):
		if self.view.text.edit_modified():
			if not askyesno(Prog, 'Text has changed: discard changes?'):
				return
		self.currfile = None
		self.view.clearAllText()
		self.view.text.edit_reset()
		self.view.text.edit_modified(0)
		#self.knownEncoding = None
	
	def run(self):
		self.root.title('VOAdict')
		self.root.mainloop()

	def getContentsList(self):
		page = requests.get('https://learningenglish.voanews.com/z/952')
		#soup = bs4.BeautifulSoup(page.text, 'lxml')
		soup = bs4.BeautifulSoup(page.text, 'html.parser')

		voalist = []
		for tag in soup.find_all('div', class_='content'):
			href = tag.find('a')
			if not href:
				continue
			href = href.attrs['href']

			date = tag.find('span', attrs={'class':'date'})
			if not date:
				continue
			date = date.text.strip()

			title = tag.find('span', attrs={'class':'title'})
			if not title:
				continue
			title = title.text.strip()

			voalist.append((href, date, title))

		return voalist

	def getCurrentURL(self):
		i = self.listb.curselection()[0]
		return 'https://learningenglish.voanews.com'+self.voalist[i][0]

	def openURL(self):
		import webbrowser
		webbrowser.open_new(self.getCurrentURL())

	def mp3towav(self, filename):
		import pydub
		sound = pydub.AudioSegment.from_mp3(filename)
		wavfile = filename.split('.')[0] + '.wav'
		sound.export(wavfile, format="wav")
		return wavfile

	def openWavFile(self, wavfile):
		def errorForAudioFile(fname):
			showerror(Prog, 'cannot open audio file ' + fname)

		if not wavfile or not os.path.isfile(wavfile):
			errorForAudioFile(wavfile)
			return False

		if not self.model.onOpen(wavfile):
			errorForAudioFile(wavfile)
			return False

		return True

	def openVOAAudio(self):
		url = self.getCurrentURL()
		page = requests.get(url)
		soup = bs4.BeautifulSoup(page.text, 'html.parser')

		tag = soup.find_all('a', attrs={'class':'handler', 'title':'64 kbps | MP3'})

		href = tag[0].attrs['href']
		filename = 'today.mp3'
		mp3file = requests.get(href)
		with open(filename, 'wb') as f:
			f.write(mp3file.content)

		wavfile = self.mp3towav(filename)
		if wavfile:
			self.openWavFile(wavfile)

		self.win_voa.destroy()

	def onOpenVOA(self):
		self.voalist = self.getContentsList()
		if not self.voalist:
			showerror(Prog, 'Cannot find VOA site')
			return False

		self.win_voa = tk.Toplevel()
		self.win_voa.title(Prog + 'Contents List')
		
		sbar = tk.Scrollbar(self.win_voa)
		sbar.pack(side=tk.RIGHT, fill=tk.Y)
		self.listb = tk.Listbox(self.win_voa, width=80, yscrollcommand=sbar.set)
		#self.listb.bind('<Double-1>', self.listb_doubleclick)
		self.listb.pack(fill=tk.BOTH, expand=True)
		sbar.config(command=self.listb.yview)

		tk.Button(self.win_voa, text='Open Audio', command=self.openVOAAudio).pack(side=tk.RIGHT)
		tk.Button(self.win_voa, text='Open URL', command=self.openURL).pack(side=tk.RIGHT)
		for i, t in enumerate(self.voalist):
			txt = t[1] + ' ' + t[2]
			self.listb.insert(i, txt)

		self.listb.selection_set(first=0)
		self.listb.focus_set()
		return True

	def onOpenAudio(self):
		wave_file = self.my_askopenfilename()
		return self.openWavFile(wave_file)

	def onPlayOrStop(self):
		if not self.model.isOpened():
			showinfo(Prog, 'Open audio file (File->OpenAuduio)')
			return

		#if self.model.isPaused():
		#	self.view.BTN_PNS.configure(text='->')
		#else:
		#	self.view.BTN_PNS.configure(text='II')
		self.model.togglePause()

	def onQuit(self):
		if self.view.text.edit_modified():
			if not askyesno(Prog, 'Discard changes?'):
				return
		self.model.onClose()
		self.root.quit()

	def onUndo(self):
		try:
			self.view.text.edit_undo()
		except TclError:
			showinfo(Prog, 'Nothing to undo')

	def onRedo(self):
		try:
			self.view.text.edit_redo()
		except TclError:
			showinfo(Prog, 'Nothing to redo')

	def onCopy(self):
		if not self.view.text.tag_ranges(tk.SEL):
			showerror(Prog, 'No text selected')
		else:
			text = self.view.text.get(tk.SEL_FIRST, tk.SEL_LAST)
			self.clipboard_clear()
			self.clipboard_append(text)

	def onDelete(self):
		if not self.view.text.tag_ranges(tk.SEL):
			showerror(Prog, 'No text selected')
		else:
			self.view.text.delete(tk.SEL_FIRST, tk.SEL_LAST)

	def onCut(self):
		if not self.view.text.tag_ranges(tk.SEL):
			showerror(Prog, 'No text selected')
		else:
			self.opCopy()
			self.onDelete()

	def onPaste(self):
		try:
			text = self.selection_get(selection='CLIPBOARD')
		except TclError:
			showerror(Prog, 'Nothing to paste')
			return
		self.view.text.insert(tk.INSERT, text)
		self.view.text.tag_remove(tk.SEL, '1.0', tk.END)
		self.view.text.tag_add(tk.SEL, tk.INSERT+'-%dc' % len(text), tk.INSERT)
		self.view.text.see(tk.INSERT)

	def onSelectAll(self):
		self.view.text.tag_add(tk.SEL, '1.0', tk.END+'-1c')   #end-1c: 1 ch back from end 
		self.view.text.mark_set(tk.INSERT, '1.0')
		self.view.text.see(tk.INSERT)

	def onGoto(self, forceline=None):
		line = forceline or askinteger(Prog, 'Enter line number')
		self.view.text.update()
		self.view.text.focus()
		if line is not None:
			maxindex = self.view.text.index(tk.END+'-1c')
			maxline = int(maxindex.split('.')[0])
			if line > 0 and line <= maxline:
				self.view.text.mark_set(tk.INSERT, '%d.0' % line)   #goto line
				self.view.text.tag_remove(tk.SEL, '1.0', tk.END)	   #delete selects
				self.view.text.tag_add(tk.SEL, tk.INSERT, 'insert + 1l')#select line
				self.view.text.see(tk.INSERT)					   #scroll to line
			else:
				showerror(Prog, 'Bad line number')

	def onFind(self, lastkey=None):
		key = lastkey or askstring(Prog, 'Enter search string')
		self.view.text.update()
		self.view.text.focus()
		self.lastfind = key
		if key:
			nocase = configs.get('caseinsens', True)
			where = self.view.text.search(key, tk.INSERT, tk.END, nocase=nocase)
			if not where:
				showerror(Prog, 'String not found')
			else:
				pastkey = where + '+%dc' % len(key)
				self.view.text.tag_remove(tk.SEL, '1.0', tk.END)
				self.view.text.tag_add(tk.SEL, where, pastkey)
				self.view.text.mark_set(tk.INSERT, pastkey)
				self.view.text.see(where)
	
	def onRefind(self):
		self.onFind(self.lastfind)

	def onDoChange(self, findtext, changeto):
		if self.view.text.tag_ranges(tk.SEL):
			self.view.text.delete(tk.SEL_FIRST, tk.SEL_LAST)
			self.view.text.insert(tk.INSERT, changeto)
			self.view.text.see(tk.INSERT)
			self.onFind(findtext)
			self.view.text.update()

	def onChange(self):
		new = tk.Toplevel()
		new.title(Prog + '- change')
		tk.Label(new, text='Find text', width=15).grid(row=0, column=0)
		tk.Label(new, text='Change to', width=15).grid(row=1, column=0)
		entry1 = tk.Entry(new)
		entry2 = tk.Entry(new)
		entry1.grid(row=0, column=1, sticky=tk.EW)
		entry2.grid(row=1, column=1, sticky=tk.EW)

		def onFind():
			self.onFind(entry1.get())

		def onApply():
			self.onDoChange(entry1.get(), entry2.get())

		tk.Button(new, text='Find', command=onFind).grid(row=0, column=2, sticky=tk.EW)
		tk.Button(new, text='Apply', command=onApply).grid(row=1, column=2, sticky=tk.EW)
		new.columnconfigure(1, weight=1)
		

if __name__ == '__main__':
	try:
		noteName = sys.argv[1]
	except IndexError:
		noteName = None

	c = Controller(noteName)
	c.run()

