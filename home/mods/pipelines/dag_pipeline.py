from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import itertools

# internal imports
import six
from mods.pipelines import pipeline


class DagOutput(object):

    def __init__(self, name=None):

        self.name = name
        self.output_type = None
        self.input_type = None
        self.mw = None

    def __eq__(self, other):
        return isinstance(other, DagOutput) and other.name == self.name

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return 'DagOutput(%s)' % self.name


class DagInput(object):

    def __init__(self, type_):

        self.output_type = type_
        self.mw = None

    def __eq__(self, other):
        return isinstance(other, DagInput) and other.output_type == self.output_type

    def __hash__(self):
        return hash(self.output_type)

    def __repr__(self):
        return 'DagInput(%s)' % self.output_type


def _all_are_type(elements, target_type):

    return all(isinstance(elem, target_type) for elem in elements)


class InvalidDAGException(Exception):

    pass


class DuplicateNameException(Exception):
    
    pass


class BadTopologyException(Exception):
    pass


class NotConnectedException(Exception):
    pass


class TypeMismatchException(Exception):
    pass


class BadInputOrOutputException(Exception):
    pass


class InvalidDictionaryOutput(Exception):
    pass


class InvalidTransformOutputException(Exception):
    pass


class DAGPipeline(pipeline.Pipeline):

    def __init__(self, dag, mod_writer, pipeline_name='DAGPipeline'):

        # Expand DAG shorthand.
        self.dag = dict(self._expand_dag_shorthands(dag))

        # Make sure DAG is valid.
        # DagInput types match output types. Nothing depends on outputs.
        # Things that require input get input. DAG is composed of correct types.
        for unit, dependency in self.dag.items():
            if not isinstance(unit, (pipeline.Pipeline, DagOutput)):
                raise InvalidDAGException(
                    'Dependency {%s: %s} is invalid. Left hand side value %s must '
                    'either be a Pipeline or DagOutput object'
                    % (unit, dependency, unit))
            if isinstance(dependency, dict):
                if not all([isinstance(name, six.string_types) for name in dependency]):
                    raise InvalidDAGException(
                        'Dependency {%s: %s} is invalid. Right hand side keys %s must be '
                        'strings' % (unit, dependency, dependency.keys()))
                values = dependency.values()
            else:
                values = [dependency]
            for subordinate in values:
                if not (isinstance(subordinate, pipeline.Pipeline) or
                        (isinstance(subordinate, pipeline.PipelineKey) and
                         isinstance(subordinate.unit, pipeline.Pipeline)) or
                        isinstance(subordinate, DagInput)):
                    raise InvalidDAGException(
                        'Dependency {%s: %s} is invalid. Right hand side subordinate %s '
                        'must be either a Pipeline, PipelineKey, or DagInput object'
                        % (unit, dependency, subordinate))

            # Check that all input types match output types.
            if isinstance(unit, DagOutput):
                # DagOutput objects don't know their types.
                continue
            if unit.input_type != self._get_type_signature_for_dependency(dependency):
                raise TypeMismatchException(
                    'Invalid dependency {%s: %s}. Required `input_type` of left hand '
                    'side is %s. DagOutput type of right hand side is %s.'
                    % (unit, dependency, unit.input_type,
                       self._get_type_signature_for_dependency(dependency)))

        # Make sure all Pipeline names are unique, so that Statistic objects don't
        # clash.
        sorted_unit_names = sorted(
            [(unit, unit.name) for unit in self.dag],
            key=lambda t: t[1])
        for index, (unit, name) in enumerate(sorted_unit_names[:-1]):
            if name == sorted_unit_names[index + 1][1]:
                other_unit = sorted_unit_names[index + 1][0]
                raise DuplicateNameException(
                    'Pipelines %s and %s both have name "%s". Each Pipeline must have '
                    'a unique name.' % (unit, other_unit, name))

        # Find DagInput and DagOutput objects and make sure they are being used
        # correctly.
        self.outputs = [
            unit for unit in self.dag if isinstance(unit, DagOutput)]
        self.output_names = dict([(output.name, output)
                                  for output in self.outputs])
        for output in self.outputs:
            output.input_type = output.output_type = (
                self._get_type_signature_for_dependency(self.dag[output]))
        inputs = set()
        for deps in self.dag.values():
            units = self._get_units(deps)
            for unit in units:
                if isinstance(unit, DagInput):
                    inputs.add(unit)
        if len(inputs) != 1:
            if not inputs:
                raise BadInputOrOutputException(
                    'No DagInput object found. DagInput is the start of the pipeline.')
            else:
                raise BadInputOrOutputException(
                    'Multiple DagInput objects found. Only one input is supported.')
        if not self.outputs:
            raise BadInputOrOutputException(
                'No DagOutput objects found. DagOutput is the end of the pipeline.')
        self.input = inputs.pop()

        # Compute output_type for self and call super constructor.
        output_signature = dict([(output.name, output.output_type)
                                 for output in self.outputs])
        super(DAGPipeline, self).__init__(
            input_type=self.input.output_type,
            output_type=output_signature,
            name=pipeline_name,
            mod_writer=mod_writer)

        # Make sure all Pipeline objects have DAG vertices that feed into them,
        # and feed their output into other DAG vertices.
        all_subordinates = (
            set([dep_unit for unit in self.dag
                 for dep_unit in self._get_units(self.dag[unit])])
            .difference(set([self.input])))
        all_destinations = set(self.dag.keys()).difference(set(self.outputs))
        if all_subordinates != all_destinations:
            units_with_no_input = all_subordinates.difference(all_destinations)
            units_with_no_output = all_destinations.difference(
                all_subordinates)
            if units_with_no_input:
                raise NotConnectedException(
                    '%s is given as a dependency in the DAG but has nothing connected '
                    'to it. Nothing in the DAG feeds into it.'
                    % units_with_no_input.pop())
            else:
                raise NotConnectedException(
                    '%s is given as a destination in the DAG but does not output '
                    'anywhere. It is a deadend.' % units_with_no_output.pop())

        # Construct topological ordering to determine the execution order of the
        # pipelines.
        # https://en.wikipedia.org/wiki/Topological_sorting#Kahn.27s_algorithm

        # `graph` maps a pipeline to the pipelines it depends on. Each dict value
        # is a list with the dependency pipelines in the 0th position, and a count
        # of forward connections to the key pipeline (how many pipelines use this
        # pipeline as a dependency).
        graph = dict([(unit, [self._get_units(self.dag[unit]), 0])
                      for unit in self.dag])
        graph[self.input] = [[], 0]
        for unit, (forward_connections, _) in graph.items():
            for to_unit in forward_connections:
                graph[to_unit][1] += 1
        # Topologically sorted elements go here.
        self.call_list = call_list = []
        nodes = set(self.outputs)
        while nodes:
            n = nodes.pop()
            call_list.append(n)
            for m in graph[n][0]:
                graph[m][1] -= 1
                if graph[m][1] == 0:
                    nodes.add(m)
                elif graph[m][1] < 0:
                    raise Exception(
                        'Congratulations, you found a bug! Please report this issue at '
                        'https://github.com/tensorflow/magenta/issues and copy/paste the '
                        'following: dag=%s, graph=%s, call_list=%s' % (self.dag, graph,
                                                                       call_list))
        # Check for cycles by checking if any edges remain.
        for unit in graph:
            if graph[unit][1] != 0:
                raise BadTopologyException(
                    'Dependency loop found on %s' % unit)

        # Note: this exception should never be raised. Disconnected graphs will be
        # caught where NotConnectedException is raised. If this exception goes off
        # there is likely a bug.
        if set(call_list) != set(
                list(all_subordinates) + self.outputs + [self.input]):
            raise BadTopologyException('Not all pipelines feed into an output or '
                                       'there is a dependency loop.')

        call_list.reverse()
        assert call_list[0] == self.input

    def _expand_dag_shorthands(self, dag):

        for key, val in dag.items():
            # Direct connection.
            if (isinstance(key, pipeline.Pipeline) and
                isinstance(val, pipeline.Pipeline) and
                isinstance(key.input_type, dict) and
                    key.input_type == val.output_type):
                yield key, dict([(name, val[name]) for name in val.output_type])
            elif key == DagOutput():
                if (isinstance(val, pipeline.Pipeline) and
                        isinstance(val.output_type, dict)):
                    dependency = [(name, val[name])
                                  for name in val.output_type]
                elif isinstance(val, dict):
                    dependency = val.items()
                else:
                    raise InvalidDictionaryOutput(
                        'DagOutput() with no name can only be connected to a dictionary '
                        'or a Pipeline whose output_type is a dictionary. Found '
                        'DagOutput() connected to %s' % val)
                for name, subordinate in dependency:
                    yield DagOutput(name), subordinate
            elif isinstance(key, DagOutput):
                if isinstance(val, dict):
                    raise InvalidDictionaryOutput(
                        'DagOutput("%s") which has name "%s" can only be connected to a '
                        'single input, not dictionary %s. Use DagOutput() without name '
                        'instead.' % (key.name, key.name, val))
                if (isinstance(val, pipeline.Pipeline) and
                        isinstance(val.output_type, dict)):
                    raise InvalidDictionaryOutput(
                        'DagOutput("%s") which has name "%s" can only be connected to a '
                        'single input, not pipeline %s which has dictionary '
                        'output_type %s. Use DagOutput() without name instead.'
                        % (key.name, key.name, val, val.output_type))
                yield key, val
            else:
                yield key, val

    def _get_units(self, dependency):
        dep_list = []
        if isinstance(dependency, dict):
            dep_list.extend(dependency.values())
        else:
            dep_list.append(dependency)
        return [self._validate_subordinate(sub) for sub in dep_list]

    def _validate_subordinate(self, subordinate):
        if isinstance(subordinate, pipeline.Pipeline):
            return subordinate
        if isinstance(subordinate, pipeline.PipelineKey):
            if not isinstance(subordinate.unit, pipeline.Pipeline):
                raise InvalidDAGException(
                    'PipelineKey object %s does not have a valid Pipeline'
                    % subordinate)
            return subordinate.unit
        if isinstance(subordinate, DagInput):
            return subordinate
        raise InvalidDAGException(
            'Looking for Pipeline, PipelineKey, or DagInput object, but got %s'
            % type(subordinate))

    def _get_type_signature_for_dependency(self, dependency):
        if isinstance(dependency,
                      (pipeline.Pipeline, pipeline.PipelineKey, DagInput)):
            return dependency.output_type
        return dict([(name, sub_dep.output_type)
                     for name, sub_dep in dependency.items()])

    def _get_outputs_as_signature(self, dependency, outputs):

        def _get_outputs_for_key(unit_or_key, outputs):
            if isinstance(unit_or_key, pipeline.PipelineKey):
                if not outputs[unit_or_key.unit]:
                    # If there are no outputs, just return nothing.
                    return outputs[unit_or_key.unit]
                assert isinstance(outputs[unit_or_key.unit], dict)
                return outputs[unit_or_key.unit][unit_or_key.key]
            assert isinstance(unit_or_key, (pipeline.Pipeline, DagInput))
            return outputs[unit_or_key]
        if isinstance(dependency, dict):
            return dict([(name, _get_outputs_for_key(unit_or_key, outputs))
                         for name, unit_or_key in dependency.items()])
        return _get_outputs_for_key(dependency, outputs)

    def _get_inputs_for_unit(self, unit, results,
                             list_operation=itertools.product):

        previous_outputs = self._get_outputs_as_signature(
            self.dag[unit], results)

        if isinstance(previous_outputs, dict):
            names = list(previous_outputs.keys())
            lists = [previous_outputs[name] for name in names]
            stack = list_operation(*lists)
            return [dict(zip(names, values)) for values in stack]
        else:
            return previous_outputs

    def _join_lists_or_dicts(self, outputs, unit):

        if not outputs:
            return []
        if isinstance(unit.output_type, dict):
            concated = dict([(key, list()) for key in unit.output_type.keys()])
            for d in outputs:
                if not isinstance(d, dict):
                    raise InvalidTransformOutputException(
                        'Expected dictionary output for %s with output type %s but '
                        'instead got type %s' % (unit, unit.output_type, type(d)))
                if set(d.keys()) != set(unit.output_type.keys()):
                    raise InvalidTransformOutputException(
                        'Got dictionary output with incorrect keys for %s. Got %s. '
                        'Expected %s' % (unit, d.keys(), unit.output_type.keys()))
                for k, val in d.items():
                    if not isinstance(val, list):
                        raise InvalidTransformOutputException(
                            'DagOutput from %s for key %s is not a list.' % (unit, k))
                    if not _all_are_type(val, unit.output_type[k]):
                        raise InvalidTransformOutputException(
                            'Some outputs from %s for key %s are not of expected type %s. '
                            'Got types %s' % (unit, k, unit.output_type[k],
                                              [type(inst) for inst in val]))
                    concated[k] += val
        else:
            concated = []
            for l in outputs:
                if not isinstance(l, list):
                    raise InvalidTransformOutputException(
                        'Expected list output for %s with outpu type %s but instead got '
                        'type %s' % (unit, unit.output_type, type(l)))
                if not _all_are_type(l, unit.output_type):
                    raise InvalidTransformOutputException(
                        'Some outputs from %s are not of expected type %s. Got types %s'
                        % (unit, unit.output_type, [type(inst) for inst in l]))
                concated += l
        return concated

    def transform(self, input_object):

        def stats_accumulator(unit, unit_inputs, cumulative_stats):
            for single_input in unit_inputs:
                results_ = unit.transform(single_input)
                stats = unit.get_stats()
                cumulative_stats.extend(stats)
                yield results_

        stats = []
        results = {self.input: [input_object]}
        for unit in self.call_list[1:]:
            if unit.mw == None:
                unit.mw = self.mw

            if isinstance(unit, DagOutput):
                unit_outputs = self._get_outputs_as_signature(
                    self.dag[unit], results)
            else:
                unit_inputs = self._get_inputs_for_unit(unit, results)
                if not unit_inputs:
                    # If this unit has no inputs don't run it.
                    results[unit] = []
                    continue
                unjoined_outputs = list(
                    stats_accumulator(unit, unit_inputs, stats))
                unit_outputs = self._join_lists_or_dicts(
                    unjoined_outputs, unit)

            self.mw.write(self.mw.model_dir, unit.name, unit_outputs)
            results[unit] = unit_outputs

        self._set_stats(stats)
        return dict([(output.name, results[output]) for output in self.outputs])
