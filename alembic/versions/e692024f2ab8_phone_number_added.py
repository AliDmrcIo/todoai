"""phone number added

Revision ID: e692024f2ab8
Revises: 
Create Date: 2025-04-22 07:55:35.056092

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e692024f2ab8'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None: # Migrigation'ın database'e sonradan yapılacak olan değişikliği halihazırda olan columnları ve verileri koruyarak ve hata almadan yapabileceğimiz yer. Yani burada halihazırda olan database'e bir şeyler ekleyeceğiz
    op.add_column('users', sa.Column('phone_number', sa.String(), nullable=True)) #user table isimli database'ime sonradan eklediğim phone_number columnını sorun çıkartmaması için sonradan bu şekilde ekledim


def downgrade() -> None: # yaptığımız değişikliği sileceğimiz kısım. örn: yapmaktan vazgeçtik, eklediğimiz column'ı silmek istiyoruz, burada yapıcaz
    pass
