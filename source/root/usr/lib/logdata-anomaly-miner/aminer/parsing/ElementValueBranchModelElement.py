"""
This module defines a model element that allows branches depending on the value of the previous model value.

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.
This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.
"""


from aminer.parsing.ModelElementInterface import ModelElementInterface
from aminer.parsing.MatchElement import MatchElement
from aminer.AminerConfig import DEBUG_LOG_NAME
from aminer import AminerConfig
from typing import Union
import logging


class ElementValueBranchModelElement(ModelElementInterface):
    """This class defines an element that selects a branch path based on a previous model value."""

    def __init__(self, element_id: str, value_model: ModelElementInterface, value_path: Union[str, None], branch_model_dict: dict,
                 default_branch: Union[str, int] = None):
        """
        Create the branch model element.
        @param value_path the relative path to the target value from the value_model element on. When the path does not resolve
        to a value, this model element will not match. A path value of None indicates, that the match element of the value_model
        should be used directly.
        @param branch_model_dict a dictionary to select a branch for the value identified by valuePath.
        @param default_branch when lookup in branch_model_dict fails, use this as default branch or fail when None.
        """
        if not isinstance(element_id, str):
            msg = "element_id has to be of the type string."
            logging.getLogger(DEBUG_LOG_NAME).error(msg)
            raise TypeError(msg)
        if len(element_id) < 1:
            msg = "element_id must not be empty."
            logging.getLogger(DEBUG_LOG_NAME).error(msg)
            raise ValueError(msg)
        self.element_id = element_id

        if not isinstance(value_model, ModelElementInterface):
            msg = "value_model has to be of the type ModelElementInterface."
            logging.getLogger(DEBUG_LOG_NAME).error(msg)
            raise TypeError(msg)
        self.value_model = value_model

        if value_path is not None:
            if not isinstance(value_path, str):
                msg = "value_path has to be of the type string or None."
                logging.getLogger(DEBUG_LOG_NAME).error(msg)
                raise TypeError(msg)
            if len(value_path) < 1:
                msg = "value_path must not be empty."
                logging.getLogger(DEBUG_LOG_NAME).error(msg)
                raise ValueError(msg)
        self.value_path = value_path

        if not isinstance(branch_model_dict, dict):
            msg = "branch_model_dict has to be of the type dict."
            logging.getLogger(DEBUG_LOG_NAME).error(msg)
            raise TypeError(msg)
        for val in branch_model_dict.values():
            if not isinstance(val, ModelElementInterface):
                msg = "all branch_model_dict values have to be of the type ModelElementInterface."
                logging.getLogger(DEBUG_LOG_NAME).error(msg)
                raise TypeError(msg)
        self.branch_model_dict = branch_model_dict

        if default_branch is not None and not isinstance(default_branch, ModelElementInterface):
            msg = "default_branch has to be of the type string or None."
            logging.getLogger(DEBUG_LOG_NAME).error(msg)
            raise TypeError(msg)
        self.default_branch = default_branch

    def get_id(self):
        """Get the element ID."""
        return self.element_id

    def get_child_elements(self):
        """
        Get all possible child model elements of this element.
        If this element implements a branching model element, then not all child element IDs will be found in matches produced by
        get_match_element.
        @return a list with all children
        """
        all_children = [self.value_model] + list(self.branch_model_dict.values())
        if self.default_branch is not None:
            all_children.append(self.default_branch)
        return all_children

    def get_match_element(self, path: str, match_context):
        """
        Try to find a match on given data for the test model and the selected branch.
        @param path the model path to the parent model element invoking this method.
        @param match_context an instance of MatchContext class holding the data context to match against.
        @return the matchElement or None if the test model did not match, no branch was selected or the branch did not match.
        """
        current_path = "%s/%s" % (path, self.element_id)
        start_data = match_context.match_data
        model_match = self.value_model.get_match_element(current_path, match_context)
        if model_match is None:
            return None

        # Now extract the test path value from the model_match. From here on, the matchContext is already modified so we must NEVER just
        # return but revert the changes in the context first.
        remaining_value_path = self.value_path
        test_match = model_match
        current_test_path = test_match.get_path()
        while remaining_value_path is not None:
            next_part_pos = remaining_value_path.find('/')
            if next_part_pos <= 0:
                current_test_path += '/' + remaining_value_path
                remaining_value_path = None
            else:
                current_test_path += '/' + remaining_value_path[:next_part_pos]
                remaining_value_path = remaining_value_path[next_part_pos + 1:]
            match_children = test_match.get_children()
            test_match = None
            if match_children is None:
                break
            for child in match_children:
                if child.get_path() == current_test_path:
                    test_match = child
                    break

        branch_match = None
        if test_match is not None:
            if isinstance(test_match.get_match_object(), bytes):
                branch_model = self.branch_model_dict.get(test_match.get_match_object().decode(AminerConfig.ENCODING), self.default_branch)
            else:
                branch_model = self.branch_model_dict.get(test_match.get_match_object(), self.default_branch)
            if branch_model is not None:
                branch_match = branch_model.get_match_element(current_path, match_context)
        if branch_match is None:
            match_context.match_data = start_data
            return None
        return MatchElement(current_path, start_data[:len(start_data) - len(match_context.match_data)],
                            start_data[:len(start_data) - len(match_context.match_data)], [model_match, branch_match])
