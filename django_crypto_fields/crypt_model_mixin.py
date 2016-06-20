from django.db import models


class CryptModelManager(models.Manager):

    def get_by_natural_key(self, value_as_hash, algorithm, mode):
        return self.get(hash=value_as_hash, algorithm=algorithm, mode=mode)


class CryptModelMixin(models.Model):

    """ A secrets lookup model searchable by hash """

    hash = models.CharField(
        verbose_name="Hash",
        max_length=128,
        db_index=True,
        unique=True)

    secret = models.BinaryField(
        verbose_name="Secret")

    algorithm = models.CharField(
        max_length=25,
        db_index=True,
        null=True)

    mode = models.CharField(
        max_length=25,
        db_index=True,
        null=True)

    objects = CryptModelManager()

    def natural_key(self):
        return (self.hash, self.algorithm, self.mode)

    class Meta:
        abstract = True
        verbose_name = 'Crypt'
        unique_together = (('hash', 'algorithm', 'mode'),)