# Generated migration to fix SectionAssignment FK

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def cleanup_orphan_assignments(apps, schema_editor):
    """
    Remove assignments without rdl_registration (orphans).
    These are assignments where the RDL was deleted but the assignment remained.
    Also remove inactive assignments since we're removing the is_active field.
    """
    SectionAssignment = apps.get_model('sections', 'SectionAssignment')

    # Remove orphans (no rdl_registration)
    orphans = SectionAssignment.objects.filter(rdl_registration__isnull=True)
    orphan_count = orphans.count()
    if orphan_count > 0:
        print(f"\n  Removing {orphan_count} orphan assignments (no rdl_registration)...")
        orphans.delete()

    # Remove inactive assignments
    inactive = SectionAssignment.objects.filter(is_active=False)
    inactive_count = inactive.count()
    if inactive_count > 0:
        print(f"\n  Removing {inactive_count} inactive assignments...")
        inactive.delete()


def noop(apps, schema_editor):
    """Reverse migration - nothing to do."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('sections', '0006_add_rdl_registration_to_assignment'),
    ]

    operations = [
        # Step 1: Clean up orphan and inactive assignments
        migrations.RunPython(cleanup_orphan_assignments, noop),

        # Step 2: Remove old unique_together constraint
        migrations.AlterUniqueTogether(
            name='sectionassignment',
            unique_together=set(),
        ),

        # Step 3: Make rdl_registration required and CASCADE on delete
        migrations.AlterField(
            model_name='sectionassignment',
            name='rdl_registration',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='section_assignments',
                to='sections.rdlregistration',
                verbose_name='registrazione RDL',
                help_text='RDL dal pool approvati - cancellando l\'RDL si cancella l\'assegnazione'
            ),
        ),

        # Step 4: Make user optional (keep for audit/history, but derive from rdl_registration)
        migrations.AlterField(
            model_name='sectionassignment',
            name='user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='section_assignments',
                to=settings.AUTH_USER_MODEL,
                verbose_name='utente (legacy)',
                help_text='Derivato da rdl_registration.user'
            ),
        ),

        # Step 5: Remove is_active field
        migrations.RemoveField(
            model_name='sectionassignment',
            name='is_active',
        ),

        # Step 6: Add new unique constraint based on rdl_registration
        migrations.AddConstraint(
            model_name='sectionassignment',
            constraint=models.UniqueConstraint(
                fields=['sezione', 'consultazione', 'rdl_registration'],
                name='unique_assignment_per_rdl'
            ),
        ),

        # Step 7: Add unique constraint for role (one effettivo/supplente per sezione)
        migrations.AddConstraint(
            model_name='sectionassignment',
            constraint=models.UniqueConstraint(
                fields=['sezione', 'consultazione', 'role'],
                name='unique_role_per_sezione'
            ),
        ),
    ]
