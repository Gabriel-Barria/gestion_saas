from fastapi import APIRouter

from app.api.deps import CurrentUserDep, UserServiceDep, MembershipServiceDep
from app.schemas.user import UserResponse, UserUpdate, PasswordUpdate
from app.schemas.membership import MembershipWithTenant

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: CurrentUserDep,
):
    """
    Get current user's profile.

    **Requires JWT token in Authorization header.**

    Returns the authenticated user's profile information.
    """
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    data: UserUpdate,
    current_user: CurrentUserDep,
    user_service: UserServiceDep,
):
    """
    Update current user's profile.

    **Requires JWT token in Authorization header.**

    Only full_name can be updated. Email changes are not allowed.
    """
    user = await user_service.update(current_user.id, data)
    return UserResponse.model_validate(user)


@router.put("/me/password")
async def update_password(
    data: PasswordUpdate,
    current_user: CurrentUserDep,
    user_service: UserServiceDep,
):
    """
    Update current user's password.

    **Requires JWT token in Authorization header.**

    The current password must be provided for verification.
    """
    await user_service.update_password(
        current_user.id,
        data.current_password,
        data.new_password,
    )
    return {"message": "Password updated successfully"}


@router.get("/me/memberships", response_model=list[MembershipWithTenant])
async def get_current_user_memberships(
    current_user: CurrentUserDep,
    membership_service: MembershipServiceDep,
):
    """
    Get current user's memberships.

    **Requires JWT token in Authorization header.**

    Returns all active memberships (tenants the user can access)
    with tenant and project details.
    """
    return await membership_service.get_user_memberships(current_user.id)
