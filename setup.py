#!/usr/bin/env python

""" Setup and installation """

from setuptools import find_packages, setup

setup(
    name='farms_app',
    version='0.1',
    description=""" Visualization of FARMS simulation using ImGUI""",
    url='https://github.com/farmsim/farms_app/',
    author='farmsdev',
    author_email='biorob-farms@groupes.epfl.ch',
    license='Apache 2.0',
    packages=find_packages(),
    zip_safe=False,
    install_requires=[
        'cython',
        'numpy',
        'scipy',
        'pywavefront',
        'matplotlib',
        'tqdm',
        'pyyaml',
        # Farms
        # "farms_core @ git+https://github.com/farmsim/farms_core.git",
        # "farms_sim @ git+https://github.com/farmsim/farms_sim.git",
        # "farms_mujoco @ git+https://github.com/farmsim/farms_mujoco.git",
    ],
    entry_points={
        'console_scripts': [
            'farms-app=farms_app.app:run'
        ],
    }
)
