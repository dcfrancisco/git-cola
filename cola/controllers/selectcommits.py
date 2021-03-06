"""This module provides a controller for selecting commits

"""
from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

from cola import gitcmds
from cola import qtutils
from cola.prefs import diff_font
from cola.views.selectcommits import SelectCommitsView
from cola.qobserver import QObserver
from cola.controllers.createbranch import create_new_branch
from cola.main.model import MainModel

#+-------------------------------------------------------------
def select_commits(title, revs, summaries, multiselect=True):
    """Use the SelectCommitsView to select commits from a list."""
    model = MainModel()
    parent = qtutils.active_window()
    view = SelectCommitsView(parent, qtutils.tr(title), multiselect=multiselect)
    ctl = SelectCommitsController(model, view, revs, summaries)
    return ctl.select_commits()


class SelectCommitsController(QObserver):
    """Select a commit from parallel rev and summary lists"""

    def __init__(self, model, view, revs, summaries):
        QObserver.__init__(self, model, view)

        self.model.set_revisions(revs)
        self.model.set_summaries(summaries)

        self.connect(view.commit_list,
                     SIGNAL('itemSelectionChanged()'),
                     self.commit_sha1_selected)
        view.commit_list.contextMenuEvent = self.context_menu_event
        self.view.commit_text.setFont(diff_font())

    def select_commits(self):
        summaries = self.model.summaries
        if not summaries:
            msg = self.tr('No commits exist in this branch.')
            qtutils.log(1, msg)
            return []
        qtutils.set_items(self.view.commit_list, summaries)
        self.view.show()
        if self.view.exec_() != QtGui.QDialog.Accepted:
            return []
        revs = self.model.revisions
        list_widget = self.view.commit_list
        return qtutils.selection_list(list_widget, revs)

    def context_menu_event(self, event):
        menu = QtGui.QMenu(self.view);
        menu.addAction(self.tr('Checkout'), self.checkout_commit)
        menu.addAction(self.tr('Create Branch here'), self.create_branch_at)
        menu.addAction(self.tr('Cherry Pick'), self.cherry_pick)
        menu.exec_(self.view.commit_list.mapToGlobal(event.pos()))

    def checkout_commit(self):
        row, selected = qtutils.selected_row(self.view.commit_list)
        if not selected:
            return
        sha1 = self.model.revision_sha1(row)
        qtutils.log(*self.model.git.checkout(sha1,
                                             with_stderr=True,
                                             with_status=True))

    def create_branch_at(self):
        row, selected = qtutils.selected_row(self.view.commit_list)
        if not selected:
            return
        create_new_branch(revision=self.model.revision_sha1(row))

    def cherry_pick(self):
        row, selected = qtutils.selected_row(self.view.commit_list)
        if not selected:
            return
        sha1 = self.model.revision_sha1(row)
        qtutils.log(*self.model.git.cherry_pick(sha1,
                                                with_stderr=True,
                                                with_status=True))

    def commit_sha1_selected(self):
        row, selected = qtutils.selected_row(self.view.commit_list)
        if not selected:
            self.view.commit_text.setText('')
            self.view.revision.setText('')
            return
        # Get the sha1 and put it in the revision line
        sha1 = self.model.revision_sha1(row)
        self.view.revision.setText(sha1)
        self.view.revision.selectAll()

        # Lookup the sha1's commit
        commit_diff = gitcmds.commit_diff(sha1)
        self.view.commit_text.setText(commit_diff)

        # Copy the sha1 into the clipboard
        qtutils.set_clipboard(sha1)
