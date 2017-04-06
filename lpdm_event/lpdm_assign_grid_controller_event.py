from lpdm_base_event import LpdmBaseEvent

class LpdmAssignGridControllerEvent(LpdmBaseEvent):
    """Assign a grid controller to an EUD"""
    def __init__(self, grid_controller_id):
        LpdmBaseEvent.__init__(self)
        self.event_type = "assign_grid_controller"
        self.grid_controller_id = grid_controller_id
