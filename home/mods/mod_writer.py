import pprint, re, pdb, glob
import os.path as osp
import tensorflow as tf

dd = {'MODS_DIR': osp.dirname(osp.abspath(__file__))}
dd.update({'HOME_DIR': osp.dirname(osp.dirname(dd['MODS_DIR']))})
dd.update({'TEMP_DIR': osp.join(dd['HOME_DIR'], 'temp')})
this_dir = glob.glob(f"{dd['TEMP_DIR']}/[0-9]*")[-1]
VERSION = osp.basename(this_dir)
dd.update({'THIS_DIR': osp.join(dd['TEMP_DIR'], VERSION)})
dd.update({'MIDI_DIR': osp.join(dd['THIS_DIR'], 'midi')})
dd.update({'SEQS_DIR': osp.join(dd['THIS_DIR'], 'sequence_examples')})
dd.update({'DATA_DIR': osp.join(dd['THIS_DIR'], 'data')})
dd.update({'POLY_DIR': osp.join(dd['DATA_DIR'], 'poly')})
dd.update({'NADE_DIR': osp.join(dd['DATA_DIR'], 'nade')})
dd.update({'PERF_DIR': osp.join(dd['DATA_DIR'], 'perf')})
dd.update({'TFRC_DIR': osp.join(dd['THIS_DIR'], 'tfrecords')})
dd.update({'TFRC_NAME': 'notesequences.tfrecord'})
dd.update({'TFRC_FULL': osp.join(dd['TFRC_DIR'], dd['TFRC_NAME'])})
DIRS_DICT = dd


class ModWriter:

	def __init__(self, dd):
		self.version = VERSION
		self.dirs_dct = dd
		self.model = ''
		self.model_dir = ''
		self.config = ''
		self.counter = 0
		self.history = []
		self.append_flag = {}

	def write(self, destination, filename, content, append=(False, '')):

		def check_append():
			return [k for k in self.append_flag.keys() if filename in k]

		destination = self.dirs_dct[destination]
		if destination == self.dirs_dct[self.model_dir]:
			destination = osp.join(destination, self.config)
		check = check_append()
		if append[0] and check:
			full_path = osp.join(destination, check[0])
		else:
			filename = f'{self.counter:02}_{filename}.txt'
			full_path = osp.join(destination, filename)
			self.history.append(full_path)

		if not tf.gfile.Exists(destination):
			tf.gfile.MkDir(destination)

		xtors = extractors = ['PolyExtractor', 'PianorollExtractor',
							  'PerformanceExtractor']

		if append[0]:
			with open(full_path, 'a') as f:
				f.write(append[1])
				nc = []
				if type(content[0]) == float:
					nc = [float(f'{c:.2f}') for c in content]
				elif type(content[0][0]) == float:
					nc = [[float(f'{cf:.2f}') for cf in cl] for cl in content]
				f.write(str(nc))
			if not check:
				self.counter += 1
				self.append_flag.update({filename: True})
		elif any([xtor in filename for xtor in xtors]):
			for c_ in content:
				with open(full_path, 'w') as f:
					f.write(str(c_))
					self.counter += 1
		elif False:
			pass
		else:
			with open(full_path, 'w') as f:
				pprint.pprint(content, f)
				self.counter += 1

	def set_model(self, model):
		self.model = model
		self.model_dir = f'{model}_DIR'

	def set_config(self, config):
		self.config = config
