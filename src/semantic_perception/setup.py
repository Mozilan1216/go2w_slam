from setuptools import find_packages, setup

package_name = 'semantic_perception'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='1564448710@qq.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            # 这一行是我们要添加的： 终端命令名 = 包名.文件名:主函数名
            'semantic_detector = semantic_perception.semantic_detector:main',
            'semantic_navigator = semantic_perception.semantic_navigator:main',
        ],
    },
)
