# stdlib
import secrets
from typing import cast

# third party
from result import Err
from result import Result

# relative
from ...client.client import SyftClient
from ...serde.serializable import serializable
from ...types.errors import SyftException
from ...types.result import as_result
from ...types.syft_object import SYFT_OBJECT_VERSION_1
from ..context import ChangeContext
from ..request.request import Change
from ..response import SyftError
from ..response import SyftSuccess
from .node_peer import NodePeer
from .routes import NodeRoute


@serializable()
class AssociationRequestChange(Change):
    __canonical_name__ = "AssociationRequestChange"
    __version__ = SYFT_OBJECT_VERSION_1

    self_node_route: NodeRoute
    remote_peer: NodePeer
    challenge: bytes

    __repr_attrs__ = ["self_node_route", "remote_peer"]

    @as_result(SyftException)
    def _run(
        self, context: ChangeContext, apply: bool
    ) -> Result[tuple[bytes, NodePeer], SyftError]:
        """
        Executes the association request.

        Args:
            context (ChangeContext): The change context.
            apply (bool): A flag indicating whether to apply the association request.

        Returns:
            Result[tuple[bytes, NodePeer], SyftError]: The result of the association request.
        """
        # relative
        from .network_service import NetworkService

        if not apply:
            # TODO: implement undo for AssociationRequestChange
            raise SyftException(
                public_message="Undo not supported for AssociationRequestChange"
            )

        # Get the network service
        service_ctx = context.to_service_ctx()
        network_service = cast(
            NetworkService, service_ctx.node.get_service(NetworkService)
        )
        network_stash = network_service.stash

        # Check if remote peer to be added is via reverse tunnel
        rtunnel_route = self.remote_peer.get_rtunnel_route()
        add_rtunnel_route = (
            rtunnel_route is not None
            and self.remote_peer.latest_added_route == rtunnel_route
        )

        # If the remote peer is added via reverse tunnel, we skip ping to peer
        if add_rtunnel_route:
            network_service.set_reverse_tunnel_config(
                context=context,
                remote_node_peer=self.remote_peer,
            )
        else:
            # Pinging the remote peer to verify the connection
            try:
                # FIX: unwrap client_with_context?
                remote_client: SyftClient = self.remote_peer.client_with_context(
                    context=service_ctx
                )
                if remote_client.is_err():
                    raise SyftException(
                        public_message=(
                            f"Failed to create remote client for peer: {self.remote_peer.id}."
                            f" Error: {remote_client.err()}"
                        )
                    )
                remote_client = remote_client.ok()
                random_challenge = secrets.token_bytes(16)
                remote_res = remote_client.api.services.network.ping(
                    challenge=random_challenge
                )
            except Exception as e:
                raise SyftException(
                    public_message="Remote Peer cannot ping peer:" + str(e)
                )

            if isinstance(remote_res, SyftError):
                return Err(remote_res)

            challenge_signature = remote_res

            # Verifying if the challenge is valid
            try:
                self.remote_peer.verify_key.verify_key.verify(
                    random_challenge, challenge_signature
                )
            except Exception as e:
                raise SyftException(public_message=str(e))

        # Adding the remote peer to the network stash
        result = network_stash.create_or_update_peer(
            service_ctx.node.verify_key, self.remote_peer
        )

        if result.is_err():
            raise SyftException(public_message=str(result.err()))

        # this way they can match up who we are with who they think we are
        # Sending a signed messages for the peer to verify
        self_node_peer = self.self_node_route.validate_with_context(context=service_ctx)

        if isinstance(self_node_peer, SyftError):
            raise SyftException(public_message=self_node_peer)

        return SyftSuccess(
            message=f"Routes successfully added for peer: {self.remote_peer.name}"
        )

    # TODO: Check if calls are expecting SyftError as return type
    def apply(self, context: ChangeContext) -> SyftSuccess:
        return self._run(context, apply=True)

    def undo(self, context: ChangeContext) -> SyftSuccess:
        return self._run(context, apply=False)

    def __repr_syft_nested__(self) -> str:
        return f"Request for connection from : {self.remote_peer.name}"
