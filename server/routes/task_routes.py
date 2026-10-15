from typing import List

from fastapi import APIRouter, HTTPException, Depends

from server.server_helper.db import get_db, SessionLocal
from server.server_helper.implant_helper import Implant
from server.server_helper.provision_helper import Provision, authenticate_active_agent
from server.server_helper.tasking_helper import Tasking, TaskingRead

router = APIRouter(prefix="/tasks", tags=["tasks"])

# endpoint for agent to retrieve tasks, mark them as pending after agent picks them up
@router.get("/{session}", response_model=List[TaskingRead])
def get_tasks(
    session: str,
    db: SessionLocal = Depends(get_db),  # type: ignore
    provision: Provision = Depends(authenticate_active_agent),
):
    if session != provision.id:
        raise HTTPException(status_code=403, detail="Agent cannot use this session")

    db_implant = db.query(Implant).filter(Implant.session == session).first()
    if db_implant is None:
        raise HTTPException(status_code=404, detail="Session not found")

    tasking = (
        db.query(Tasking)
        .filter(Tasking.session == session, Tasking.complete.in_(["False", "Pending"]))
        .all()
    )
    if not tasking:
        raise HTTPException(status_code=404, detail="No tasks found for this session")
    # Mark tasks as pending
    for task in tasking:
        # implant picked it up for action
        task.complete = "Pending"
    db.commit()

    return tasking
