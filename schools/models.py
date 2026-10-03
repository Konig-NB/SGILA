from django.conf import settings
from django.db import models

SECTOR_CHOICES = [
    ('public', 'Public'),
    ('independent', 'Independent'),
    ('unknown', 'Unknown'),
]

STATUS_CHOICES = [
    ('open', 'Open'),
    ('pending open', 'Pending open'),
]

QUINTILE_CHOICES = [(n, f'Quintile {n}') for n in range(1, 6)]

# The nine provinces are a single list in settings (the dropdown and the import
# normaliser use it too); the model just needs them as value/label pairs.
PROVINCE_CHOICES = [(province, province) for province in settings.PROVINCES]


class School(models.Model):
    """
    One row from the DBE National Master List of Schools.

    Deliberately holds only the school's published details — name, place,
    quintile, sector and size. The master list also carries contact details for
    many schools; none of that is imported or stored here, because this app has
    no need for it.
    """

    emis_number = models.CharField(
        max_length=20,
        unique=True,
        help_text='DBE EMIS number. The stable identifier used to re-import updates.',
    )
    name = models.CharField(max_length=255)
    province = models.CharField(max_length=64, choices=PROVINCE_CHOICES)
    district = models.CharField(max_length=128, blank=True, default='')
    town = models.CharField(max_length=128, blank=True, default='')
    township_village = models.CharField(max_length=128, blank=True, default='')
    quintile = models.PositiveSmallIntegerField(
        choices=QUINTILE_CHOICES,
        null=True,
        blank=True,
        help_text='DBE poverty ranking, 1 (poorest) to 5. Blank when unknown.',
    )
    sector = models.CharField(
        max_length=16, choices=SECTOR_CHOICES, default='unknown'
    )
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default='open'
    )
    school_type = models.CharField(max_length=64, blank=True, default='')
    urban_rural = models.CharField(max_length=32, blank=True, default='')
    learners_2025 = models.PositiveIntegerField(
        null=True, blank=True, help_text='Learner enrolment as published for 2025.'
    )

    class Meta:
        ordering = ['name', 'emis_number']
        indexes = [
            # The autocomplete always filters by province first, then matches on
            # name, so these two carry the search.
            models.Index(fields=['province', 'name'], name='school_province_name_idx'),
            models.Index(fields=['name'], name='school_name_idx'),
            models.Index(fields=['province', 'status'], name='school_prov_status_idx'),
        ]
        verbose_name_plural = 'schools'

    def __str__(self):
        return f'{self.name} ({self.province})'

    @property
    def place_label(self):
        """
        Town (or township/village) and district, used to tell same-named schools
        apart. District is always populated in the master list; the town often
        isn't, so it falls back.
        """
        place = self.town or self.township_village
        if place and self.district:
            return f'{place} ({self.district})'
        if self.district:
            return self.district
        return place

    @property
    def display_label(self):
        """e.g. ``BALENI SECONDARY SCHOOL, Bizana (Alfred Nzo East)``."""
        place = self.place_label
        return f'{self.name}, {place}' if place else self.name

    @property
    def is_independent(self):
        return self.sector == 'independent'