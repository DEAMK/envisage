# Standard library imports.
import cPickle
import logging
import os.path

# Enthought library imports.
from enthought.etsconfig.api import ETSConfig
from enthought.envisage.api import Application, ExtensionPoint
from enthought.pyface.api import GUI, SplashScreen
from enthought.pyface.tasks.action.api import SchemaAddition
from enthought.pyface.tasks.api import TaskLayout, TaskWindowLayout
from enthought.traits.api import Bool, Callable, Dict, Event, File, \
    HasStrictTraits, Instance, List, Property, Str, Unicode

# Local imports
from task_window import TaskWindow
from task_window_event import TaskWindowEvent, VetoableTaskWindowEvent

# Logging.
logger = logging.getLogger(__name__)


class TasksApplicationState(HasStrictTraits):
    """ A class used internally by TasksApplication for saving and restoring 
        application state.
    """
    
    # A mapping from task IDs to task layouts.
    task_layouts = Dict(Str, Instance(TaskLayout))

    # Layouts for the windows extant at application exit.
    window_layouts = List(TaskWindowLayout)


class TasksApplication(Application):
    """ The entry point for an Envisage Tasks application.

    This class handles the common case for Tasks applications and is intended to
    be subclassed to modify its start/stop behavior, etc. 
    """

    # Extension point IDs.
    TASK_FACTORIES  = 'enthought.envisage.ui.tasks.tasks'
    TASK_EXTENSIONS = 'enthought.envisage.ui.tasks.task_extensions'

    #### 'TasksApplication' interface #########################################

    # The active task window (the last one to get focus).
    active_window = Instance(TaskWindow)

    # A list of schema additions that will be added to all tasks. The following
    # items are provided by default:
    #  - An Exit item in the File menu
    #  - A Group in the View menu for toggling the visibility of dock panes
    global_actions = List(SchemaAddition)

    # The PyFace GUI for the application.
    gui = Instance(GUI)

    # The name of the application (also used on window title bars).
    name = Unicode

    # The splash screen for the application. By default, there is no splash
    # scren.
    splash_screen = Instance(SplashScreen)

    # The directory on the local file system used to persist window layout
    # information.
    state_location = File

    # The list of task windows created by the application.
    windows = List(TaskWindow)

    # The factory for creating task windows.
    window_factory = Callable(TaskWindow)

    #### Application layout ###################################################

    # The default layout for the application. If not specified, a single window
    # will be created with the first available task factory.
    default_layout = List(TaskWindowLayout)

    # Whether to restore the previous *application level* layout when the
    # application is started. Even if this is False, the layout state of
    # individual tasks will be restored.
    restore_layout = Bool(True)

    #### Window lifecycle events ##############################################

    # Fired when a task window has been created.
    window_created = Event(TaskWindowEvent)

    # Fired when a task window is opening.
    window_opening = Event(VetoableTaskWindowEvent)

    # Fired when a task window has been opened.
    window_opened = Event(TaskWindowEvent)

    # Fired when a task window is closing.
    window_closing = Event(VetoableTaskWindowEvent)

    # Fired when a task window has been closed.
    window_closed = Event(TaskWindowEvent)

    #### Protected interface ##################################################

    # An 'explicit' exit is when the the 'exit' method is called.
    # An 'implicit' exit is when the user closes the last open window.
    _explicit_exit = Bool(False)

    # Task and window state.
    _state = Instance(TasksApplicationState, ())

    # Contributed TaskFactories.
    _task_factories = ExtensionPoint(id=TASK_FACTORIES)

    # Contributed TaskExtensions.
    _task_extensions = ExtensionPoint(id=TASK_EXTENSIONS)

    ###########################################################################
    # 'IApplication' interface.
    ###########################################################################

    def run(self):
        """ Run the application.
        """
        # Make sure the GUI has been created (so that, if required, the splash
        # screen is shown).
        gui = self.gui

        if self.start():
            # Create windows from the default or saved application layout.
            self._create_windows()

            # Start the GUI event loop.
            gui.start_event_loop()

    ###########################################################################
    # 'TasksApplication' interface.
    ###########################################################################

    def create_task(self, id):
        """ Creates the Task with the specified ID. Returns None if there is no
            suitable TaskFactory.
        """
        # Get the factory for the task.
        for factory in self._task_factories:
            if factory.id == id:
                break
        else:
            logger.error('No factory for task with id %r', id)
            return None

        # Create the task using suitable task extensions.
        extensions = [ ext for ext in self._task_extensions 
                       if ext.task_id == id ]
        task = factory.create_with_extensions(extensions)
        task.extra_actions.extend(self.global_actions)
        task.id = factory.id
        return task

    def create_window(self, **kw):
        """ Creates a new TaskWindow and attaches it to the application.
        """
        window = self.window_factory(application=self, **kw)

        # Listen for the window events.
        window.on_trait_change(self._on_window_activated, 'activated')
        window.on_trait_change(self._on_window_opening, 'opening')
        window.on_trait_change(self._on_window_opened, 'opened')
        window.on_trait_change(self._on_window_closing, 'closing')
        window.on_trait_change(self._on_window_closed, 'closed')

        # Event notification.
        self.window_created = TaskWindowEvent(window=window)

        return window

    def exit(self):
        """ Exits the application, closing all open task windows.

        Returns whether the application exited (whether all the windows were
        successfully closed.)

        This method is not called when the user clicks the close button or
        otherwise closes a window through his or her window manager. It is
        called only through File->Exit.
        """
        self._explicit_exit = True
        try:
            # Fetch the window layouts *before* closing the windows. If we
            # succeed in closing all the windows, we will write these to disk.
            window_layouts = [ w.get_window_layout() for w in self.windows ]

            # Attempt to close all open windows.
            success = True
            for window in reversed(self.windows):
                if not window.close():
                    success = False
                    break
            
            # Save the state, if necesssary.
            if success:
                self._state.window_layouts = window_layouts
                self._save_state(self._state)
        finally:
            self._explicit_exit = False
        return success

    ###########################################################################
    # Protected interface.
    ###########################################################################

    def _create_windows(self):
        """ Called at startup to create TaskWindows from the default or saved
            application layout.
        """
        # Build a list of TaskWindowLayouts.
        restored_state = self._load_state()
        if self.restore_layout:
            if restored_state.window_layouts:
                window_layouts = restored_state.window_layouts
            else:
                window_layouts = self.default_layout
        else:
            # Even if we are not restoring the window layout, we restore the
            # layouts of individual tasks.
            window_layouts = self.default_layout
            for window_layout in window_layouts:
                window_layout.layout_state.update(restored_state.task_layouts)

        # Create a TaskWindow for each TaskWindowLayout.
        for window_layout in window_layouts:
            window = self.create_window()
            for task_id in window_layout.tasks:
                task = self.create_task(task_id)
                if task:
                    window.add_task(task)
                else:
                    logger.error('No task with ID %r', task_id)
            window.set_window_layout(window_layout)
            window.open()

    def _load_state(self):
        """ Loads saved application state, if possible.
        """
        state = TasksApplicationState()
        filename = os.path.join(self.state_location, 'application_memento')
        if os.path.exists(filename):
            # Attempt to unpickle the saved application layout.
            try:
                with open(filename, 'r') as f:
                    state = cPickle.load(f)
            except:
                # If anything goes wrong, log the error and continue.
                logger.exception('Restoring application layout from %s',
                                 filename)
        return state

    def _save_state(self, state):
        """ Saves the specified application state.
        """
        filename = os.path.join(self.state_location, 'application_memento')
        with open(filename, 'w') as f:
            cPickle.dump(state, f)

    #### Trait initializers ###################################################

    def _default_layout_default(self):
        window_layout = TaskWindowLayout()
        if self._task_factories:
            window_layout.tasks = [ self._task_factories[0].id ]
        return [ window_layout ]

    def _global_actions_default(self):
        from action.exit_action import ExitAction
        from action.preferences_action import PreferencesGroup
        from enthought.pyface.tasks.action.api import DockPaneToggleGroup
        return [ SchemaAddition(id='Exit',
                                factory=ExitAction, 
                                path='MenuBar/File'),
                 SchemaAddition(id='Preferences',
                                factory=PreferencesGroup,
                                path='MenuBar/Edit'),
                 SchemaAddition(id='DockPaneToggleGroup',
                                factory=DockPaneToggleGroup,
                                path='MenuBar/View') ]

    def _gui_default(self):
        return GUI(splash_screen=self.splash_screen)

    def _state_location_default(self):
        state_location = os.path.join(ETSConfig.application_home,
                                      'tasks', ETSConfig.toolkit)
        if not os.path.exists(state_location):
            os.makedirs(state_location)

        logger.debug('Tasks state location is %s', state_location)

        return state_location

    #### Trait change handlers ################################################

    def _on_window_activated(self, window, trait_name, event):
        logger.debug('Task window %s activated', window)
        self.active_window = window

    def _on_window_opening(self, window, trait_name, event):
        # Event notification.
        self.window_opening = window_event = VetoableTaskWindowEvent(
            window=window)
        
        if window_event.veto:
            event.veto = True

    def _on_window_opened(self, window, trait_name, event):
        self.windows.append(window)

        # This is necessary because the activated event is not fired when a
        # window is first opened and gets focus. It is only fired when the
        # window comes from lower in the stack to be the active window.
        self.active_window = window

        # Event notification.
        self.window_opened = TaskWindowEvent(window=window)

    def _on_window_closing(self, window, trait_name, event):
        # Event notification.
        self.window_closing = window_event = VetoableTaskWindowEvent(
            window=window)
        
        if window_event.veto:
            event.veto = True
        else:
            # Store the TaskLayouts for the window.
            window_layout = window.get_window_layout()
            self._state.task_layouts.update(window_layout.layout_state)
            
            # If we're exiting implicitly and this is the last window, save
            # state, because we won't get another chance.
            if len(self.windows) == 1 and not self._explicit_exit:
                self._state.window_layouts = [ window_layout ]
                self._save_state(self._state)

    def _on_window_closed(self, window, trait_name, event):
        self.windows.remove(window)

        # Event notification.
        self.window_closed = TaskWindowEvent(window=window)

        # Was this the last window?
        if len(self.windows) == 0:
            # Invoke later to ensure that 'closed' event handlers get called
            # before 'stop()' does.
            self.gui.invoke_later(self.stop)
