"""Logique métier du domaine `foyer`."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from .models import Foyer, Invitation, MembreFoyer

_DEFAULT_FOYER_NAME = "Mon foyer"


class InvitationError(Exception):
    """Erreur métier autour des invitations."""

    code: str = "invalid"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


class EmailDejaMembreError(InvitationError):
    code = "deja_membre"


class EmailDansAutreFoyerError(InvitationError):
    code = "autre_foyer"


class InvitationDejaEnAttenteError(InvitationError):
    """Levée quand une invitation `en_attente` existe déjà pour ce couple foyer/email."""

    code = "deja_en_attente"

    def __init__(self, message: str, *, invitation: Invitation) -> None:
        super().__init__(message)
        self.invitation = invitation


class InvitationInvalideError(InvitationError):
    code = "invalide"


def compute_default_foyer_name(email: str) -> str:
    """Calcule un nom de foyer par défaut depuis une adresse e-mail.

    Extrait la partie locale (avant ``@``), prend le premier segment
    avant ``.`` ou ``+``, ne garde que les caractères alphabétiques et
    capitalise. Retourne ``"Foyer de {Nom}"`` si exploitable, sinon
    ``"Mon foyer"``.
    """
    if not email or "@" not in email:
        return _DEFAULT_FOYER_NAME

    local_part = email.split("@", 1)[0]
    head = local_part.split(".")[0].split("+")[0]
    cleaned = "".join(c for c in head if c.isalpha())

    if not cleaned:
        return _DEFAULT_FOYER_NAME

    return f"Foyer de {cleaned.capitalize()}"


@transaction.atomic
def get_or_create_foyer_for_user(user) -> Foyer:
    """Retourne le foyer de l'utilisateur, en créant un nouveau si absent.

    L'utilisateur devient le créateur et le membre unique du foyer fraîchement
    créé. Idempotent : un appel répété pour un user déjà rattaché ne crée rien.
    """
    membre = MembreFoyer.objects.select_related("foyer").filter(user=user).first()
    if membre is not None:
        return membre.foyer

    foyer = Foyer.objects.create(
        nom=compute_default_foyer_name(user.email),
        cree_par=user,
    )
    MembreFoyer.objects.create(user=user, foyer=foyer)
    return foyer


def _normaliser_email(email: str) -> str:
    return email.strip().lower()


def creer_invitation(
    *,
    foyer: Foyer,
    email: str,
    prenom: str,
    cree_par,
) -> Invitation:
    """Crée une invitation pour le couple (foyer, email).

    Lève une :class:`InvitationError` adaptée si :
    - l'email est déjà membre du foyer ;
    - l'email correspond à un user déjà membre d'un autre foyer ;
    - une invitation ``en_attente`` existe déjà pour ce couple
      (l'instance existante est attachée à l'exception).
    """
    email_norm = _normaliser_email(email)
    User = get_user_model()

    user_existant = User.objects.filter(email__iexact=email_norm).first()
    if user_existant is not None:
        membre_existant = MembreFoyer.objects.filter(user=user_existant).first()
        if membre_existant is not None:
            if membre_existant.foyer_id == foyer.pk:
                raise EmailDejaMembreError(
                    "Cette personne est déjà membre du foyer."
                )
            raise EmailDansAutreFoyerError(
                "Cette adresse appartient déjà à un autre foyer."
            )

    invitation_existante = Invitation.objects.filter(
        foyer=foyer,
        email=email_norm,
        statut=Invitation.Statut.EN_ATTENTE,
    ).first()
    if invitation_existante is not None:
        raise InvitationDejaEnAttenteError(
            "Une invitation est déjà en cours pour cette adresse.",
            invitation=invitation_existante,
        )

    try:
        return Invitation.objects.create(
            foyer=foyer,
            email=email_norm,
            prenom=prenom.strip(),
            cree_par=cree_par,
        )
    except IntegrityError as exc:  # garde-fou en cas de race condition
        raise InvitationDejaEnAttenteError(
            "Une invitation est déjà en cours pour cette adresse.",
            invitation=Invitation.objects.get(
                foyer=foyer,
                email=email_norm,
                statut=Invitation.Statut.EN_ATTENTE,
            ),
        ) from exc


def annuler_invitation(invitation: Invitation, *, par_user) -> Invitation:
    """Annule une invitation. Le caller doit déjà avoir vérifié les permissions."""
    if invitation.cree_par_id != par_user.pk:
        raise InvitationInvalideError("Seul le créateur du foyer peut annuler.")
    if invitation.statut != Invitation.Statut.EN_ATTENTE:
        raise InvitationInvalideError("Cette invitation n'est plus en attente.")
    invitation.statut = Invitation.Statut.ANNULEE
    invitation.save(update_fields=["statut"])
    return invitation


def get_invitation_utilisable(token: str) -> Invitation | None:
    """Retourne l'invitation correspondant au token si elle est utilisable, sinon ``None``."""
    invitation = (
        Invitation.objects.select_related("foyer", "cree_par")
        .filter(token=token)
        .first()
    )
    if invitation is None or not invitation.est_utilisable:
        return None
    return invitation


@transaction.atomic
def accepter_invitation(
    *,
    invitation: Invitation,
    user_existant=None,
    nouveau_password: str | None = None,
):
    """Accepte une invitation : crée le user si besoin, l'ajoute au foyer.

    Soit ``user_existant`` (déjà connecté avec l'email correspondant), soit
    ``nouveau_password`` doit être fourni. Retourne le ``User`` final.

    Garantit l'atomicité : ``MembreFoyer`` créé, ``Invitation`` marquée
    ``acceptee`` au sein de la même transaction.
    """
    if not invitation.est_utilisable:
        raise InvitationInvalideError("Cette invitation n'est plus utilisable.")

    User = get_user_model()
    invitation_email = invitation.email

    if user_existant is not None:
        if user_existant.email.lower() != invitation_email.lower():
            raise InvitationInvalideError(
                "L'utilisateur connecté ne correspond pas à l'invitation."
            )
        user = user_existant
    else:
        if nouveau_password is None:
            raise InvitationInvalideError(
                "Un mot de passe est requis pour créer le compte."
            )
        user = User.objects.filter(email__iexact=invitation_email).first()
        if user is not None:
            raise InvitationInvalideError(
                "Un compte existe déjà pour cette adresse, connecte-toi pour accepter."
            )
        user = User.objects.create_user(
            email=invitation_email,
            password=nouveau_password,
            first_name=invitation.prenom,
        )

    if MembreFoyer.objects.filter(user=user).exists():
        raise InvitationInvalideError(
            "Cet utilisateur est déjà membre d'un foyer."
        )

    MembreFoyer.objects.create(user=user, foyer=invitation.foyer)
    invitation.statut = Invitation.Statut.ACCEPTEE
    invitation.save(update_fields=["statut"])

    return user
