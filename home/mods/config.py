import os, sys, re
sys.path.insert(0, os.path.abspath('..'))

from mods.models.performance_rnn import performance_model
from mods.models.pianoroll_rnn_nade import pianoroll_rnn_nade_model
from mods.models.polyphony_rnn import polyphony_model
from mods.music.encoder_decoder import (
    OneHotEncoding,
    EventSequenceEncoderDecoder,
)

perf_configs = performance_model.default_configs
nade_configs = pianoroll_rnn_nade_model.default_configs
poly_configs = polyphony_model.default_configs

INSTS = [OneHotEncoding, EventSequenceEncoderDecoder]

ATTRS = ['_control_encoder_decoder', '_target_encoder_decoder', 
         '_encoder', '_encoders', '_encode_single_sequence', 
         '_one_hot_encoding', '_density_bin_ranges',
         '_event_ranges']

CATTRS = ['details','encoder_decoder','hparams',
          'steps_per_quarter','steps_per_second',
          'mod_writer','num_velocity_bins','density_bin_ranges',
          'density_window_size','pitch_histogram_window_size',
          'optional_conditioning',]

class ConfigsParser:

    INSTS = [OneHotEncoding, EventSequenceEncoderDecoder]

    ATTRS = ['_control_encoder_decoder', '_target_encoder_decoder', 
             '_encoder', '_encoders', '_encode_single_sequence', 
             '_one_hot_encoding', '_density_bin_ranges',
             '_event_ranges']

    CATTRS = ['details','encoder_decoder','hparams',
              'steps_per_quarter','steps_per_second',
              'mod_writer','num_velocity_bins','density_bin_ranges',
              'density_window_size','pitch_histogram_window_size',
              'optional_conditioning',]

    def __init__(self, configs):
        self.cs = configs
        self.csd = self.configsattrs(configs, CATTRS)
        self.ed_list = None
        self.parsed = []


    def configsattrs(self, default_configs, attrs):
        configsdict = {}
        for a in attrs:
            configsdict.update({a: []})
            for configs in default_configs:
                configsdict[a].append((configs, getattr(default_configs[configs], a)))

        self.csd = configsdict
        return self.csd

    def enc_dec_dict(self, class_, new_keys):
        c_name = lambda c_: c_.__class__.__name__
        new_keys = [new_keys]
        if c_name(class_) == '_ConfigsParser__class_':
            return
        if len(new_keys) == 0:
            return
        for k in new_keys:
            if k in ATTRS:
                if any([isinstance(class_, i) for i in INSTS]):
                    return {k: self.enc_dec_dict(class_, c_name(class_))}
                elif type(class_) == bool:
                    return {k: class_}
                elif all(isinstance(c, (float, int, tuple)) for c in class_):
                    return {k: class_}
                else:
                    return {k: [self.enc_dec_dict(c, c_name(c)) for c in class_]}
            else:
                nvs = []
                for attr in ATTRS:
                    if attr in dir(class_):
                        nvs.append(attr)
                if len(nvs) == 1:
                    return {c_name(class_): self.enc_dec_dict(getattr(class_, nvs[0]), nvs[0])}
                else: 
                    tmp = {c_name(class_): []}
                    for v in nvs:
                        tmp[c_name(class_)].append(self.enc_dec_dict(getattr(class_, v), v))
                    return tmp

    def create_ed_list(self):
        ed_list = []
        for c in self.csd['encoder_decoder']:
            ed_list.append(self.enc_dec_dict(c[1], c[1]))
        self.ed_list = ed_list
        return ed_list

    def parsed_ed_list(self):
        if self.ed_list == None:
            self.create_ed_list()
        if len(self.parsed) == 0:
            for ed in self.ed_list:
                self.parsed.append(self.stringify(ed))
        return self.parsed
    
    def stringify(self, ed):
        s = ''
        i = 2
        space = ' '
        brackets = []

        def pretty(ed):
            nonlocal s, i, space, brackets
            if type(ed) == bool:
                s = s[:-1]
                s += f'{ed}}}\n'
                i -= 2
                brackets = brackets[:-1]
                return
            elif type(ed) != list and type(ed) != dict:
                s += str(ed)
                brackets = brackets[:-1]
                return
            elif len(ed) == 0:
                s = s[:-1]
                s += f'[]}}\n'
                i -= 2
                brackets = brackets[:-1]
                return
            elif all(isinstance(d, (float, int, tuple)) for d in ed):
                s = s[:-1]
                s += f'{ed}}}\n'
                brackets = brackets[:-1]
                lsb = last_sqr_bracket = ''.join(brackets).rfind('[')
                ncb = n_curly_braces = len(brackets[lsb+1:])
                i = ((lsb+1)*2)+2
                s += f'{space*i}{"}"*ncb}\n'
                brackets = brackets[:-ncb]
                return
            elif type(ed) == list:
                s += f'{space*i}[\n'
                brackets.append('[')
                i += 2
                for d in ed:
                    pretty(d)
                i -= 2
                s += f'{space*i}]\n'
                brackets = brackets[:-1]
                if brackets[-1] == '[':
                    brackets = brackets[:-1]
                lsb = last_sqr_bracket = ''.join(brackets).rfind('[')
                ncb = n_curly_braces = len(brackets[lsb+1:])
                i = ((lsb+1)*2)+2
                s += f'{space*i}{"}"*ncb}\n'
                brackets = brackets[:-ncb]
                return
            else:
                k, *v = list(ed.items())[0]
                s += f'{space*i}{{{k}:\n'
                brackets.append('{')
                i += 2
                pretty(v[0])
                return

        pretty(ed)
        return s

