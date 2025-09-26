from setuptools import setup

setup(
    name='pytest-oduit',
    version='0.1.0',
    description='py.test plugin to run Odoo tests',
    url='https://github.com/oduit/pytest-oduit',
    license='AGPLv3',
    author='Holger Nahrsatedt',
    author_email='holger.nahrstaedt@hasomed.de',
    py_modules=['pytest_oduit'],
    entry_points={'pytest11': ['odoo = pytest_oduit']},
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=[
        "pytest>=8",
        "oduit-core"
    ],
    setup_requires=[
        'setuptools_scm',
    ],
    python_requires='>=3.9',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Operating System :: POSIX',
        'Topic :: Software Development :: Testing',
        'Topic :: Software Development :: Libraries',
        'Topic :: Utilities',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ]
)
