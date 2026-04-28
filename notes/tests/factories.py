import factory

from comptes.tests.factories import UserFactory
from foyer.tests.factories import MembreFoyerFactory
from notes.models import Commentaire, Note


class NoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Note

    membre = factory.SubFactory(MembreFoyerFactory)
    contenu = factory.Faker("paragraph", locale="fr_FR")


class CommentaireFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Commentaire

    note = factory.SubFactory(NoteFactory)
    auteur = factory.SubFactory(UserFactory)
    extrait = factory.Faker("sentence", locale="fr_FR")
    contenu = factory.Faker("sentence", locale="fr_FR")
