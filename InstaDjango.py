#!/usr/bin/env python3


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Versions.

django_ver = "1.8"


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Requirements.

req_base_fn = "base.txt"
req_base = """
    Django=={django_ver}
    uwsgi
    psycopg2
    pytz
    python3-memcached
    django-model-utils
    django-extensions
    django-braces
""".\
    format(django_ver=django_ver)

req_local_fn = "local.txt"
req_local = """
    -r base.txt

    coverage
    django-debug-toolbar
"""

req_staging_fn = "staging.txt"
req_staging = """
    -r base.txt
"""

req_production_fn = "production.txt"
req_production = """
    -r base.txt
"""


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Top-level shell scripts.

sync_excl = (
    "--exclude={proj}_venv --exclude=__pycache__ --exclude=staticroot --exclude=mediaroot "
    "--exclude=uwsgi/pid --exclude=uwsgi/uwsgi.log --exclude=.DS_Store")

sync_script_fn = "[Push].command"
sync_script = """
    #!/bin/bash -e

    srcparent=$( cd "$( dirname "${{BASH_SOURCE[0]}}" )" && pwd )
    src=$srcparent/{proj}
    sshkey={ssh_key}

    dstparent={remote_parent_dir}
    dst={remote_dir}
    dstuserhost={user_host}
    dstport={port}
    dstuserown={user}

    syncexcl="%s"
    rsync -az $syncexcl --delete -e "ssh -i $sshkey -p $dstport" $src $dstuserhost:$dstparent

    # findexcl="-not -path '*{proj}_venv*' -and -not -path '*uwsgi*' -and -not -path '*mediaroot*'"
    # ssh -i $sshkey -p $dstport $dstuserhost <<EOF
    #     chown -R $dstuserown:$dstuserown $dst
    #     find $dst $findexcl -type d -print0 | xargs -0 chmod 755
    #     find $dst $findexcl -type f -print0 | xargs -0 chmod 644
    #     chmod u+x $dst/s $dst/u
    # EOF
""" % sync_excl

restart_uwsgi_script_fn = "[RestartUwsgi].command"
restart_uwsgi_script = """
    #!/bin/bash -e

    sshkey={ssh_key}

    dst={remote_dir}
    dstuserhost={user_host}
    dstport={port}

    ssh -i $sshkey -p $dstport $dstuserhost <<EOF
        cd $dst/uwsgi
        . ../{proj}_venv/bin/activate
        ./re
        deactivate
    EOF
"""

sync_back_script_fn = "[Pull].command"
sync_back_script = """
    #!/bin/bash -e

    src={remote_dir}
    srcuserhost={user_host}
    srcport={port}

    dstparent=$( cd "$( dirname "${{BASH_SOURCE[0]}}" )" && pwd )
    sshkey={ssh_key}

    syncexcl="%s"
    rsync -az $syncexcl -e "ssh -i $sshkey -p $srcport" $srcuserhost:$src $dstparent
""" % (sync_excl)

make_migrations_script_fn = "[MakeMigrations].command"
make_migrations_script = """
    #!/bin/bash -e

    srcparent=$( cd "$( dirname "${{BASH_SOURCE[0]}}" )" && pwd )
    sshkey={ssh_key}

    dst={remote_dir}
    dstuserhost={user_host}
    dstport={port}

    $srcparent/%s

    ssh -i $sshkey -p $dstport $dstuserhost <<EOF
        cd $dst
        . {proj}_venv/bin/activate
        python manage.py makemigrations
        deactivate
    EOF

    $srcparent/%s
""" % (sync_script_fn, sync_back_script_fn)

make_migrations_and_migrate_script_fn = "[MakeMigrationsAndMigrate].command"
make_migrations_and_migrate_script = """
    #!/bin/bash -e

    srcparent=$( cd "$( dirname "${{BASH_SOURCE[0]}}" )" && pwd )
    sshkey={ssh_key}

    dst={remote_dir}
    dstuserhost={user_host}
    dstport={port}

    $srcparent/%s

    ssh -i $sshkey -p $dstport $dstuserhost <<EOF
        cd $dst
        . {proj}_venv/bin/activate
        python manage.py makemigrations && python manage.py migrate
        deactivate
    EOF

    $srcparent/%s
""" % (sync_script_fn, sync_back_script_fn)

server_shell_script_fn = "[AppShell].command"
server_shell_script = """
    #!/bin/bash -e

    srcparent=$( cd "$( dirname "${{BASH_SOURCE[0]}}" )" && pwd )
    sshkey={ssh_key}

    dst={remote_dir}
    dstuserhost={user_host}
    dstport={port}

    $srcparent/%s

    ssh -i $sshkey -p $dstport -t $dstuserhost "cd $dst ; echo '. ~/.bashrc ; . s ; rm tmpbashrc ; clear' > tmpbashrc ; /bin/bash --rcfile tmpbashrc"

    $srcparent/%s
""" % (sync_script_fn, sync_back_script_fn)


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Sublime Text project.

sublime_project = """
    {{
        "build_systems":
        [
            {{
                "name": "{proj} Python Builder",
                "selector": "source.python",
                "shell_cmd": "/bin/bash $project_path/%s && /bin/bash $project_path/%s"
            }}
        ],
        "folders":
        [
            {{
                "follow_symlinks": true,
                "path": "."
            }}
        ]
    }}
""" % (sync_script_fn, restart_uwsgi_script_fn)
# Alternatively: sync, restart uWSGI, and output the server's response into Sublime Text
# "shell_cmd": "/bin/bash $project_path/%s && /bin/bash $project_path/%s ; echo -e '--------------------------------\\\\n' ; curl -s {domain} ; echo -e '\\\\n\\\\n--------------------------------'"


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Settings.

settings_base = """
    import os

    from django.core.exceptions import ImproperlyConfigured


    def get_env_variable(var_name):
        try:
            return os.environ[var_name]
        except KeyError:
            error_msg = "Set the %s environment variable" % var_name
            raise ImproperlyConfigured(error_msg)


    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    SECRET_KEY = get_env_variable("DJANGO_SECRET_KEY")

    ALLOWED_HOSTS = ["{domain}"]

    INSTALLED_APPS = (
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
        "django_extensions",
    )

    MIDDLEWARE_CLASSES = (
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.auth.middleware.SessionAuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
        "django.middleware.security.SecurityMiddleware",
    )

    TIME_ZONE = "UTC"

    USE_I18N = True
    USE_L10N = True
    LANGUAGE_CODE = "en-us"
    USE_TZ = True

    ROOT_URLCONF = "{proj}.urls"
    WSGI_APPLICATION = "{proj}.wsgi.application"

    STATIC_ROOT = os.path.join(BASE_DIR, "staticroot/")
    STATIC_URL = "/static/"

    MEDIA_ROOT = os.path.join(BASE_DIR, "mediaroot/")
    MEDIA_URL = "/media/"

    TEMPLATES = [
        {{
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [os.path.join(BASE_DIR, "templates")],
            "APP_DIRS": True,
            "OPTIONS": {{
                "context_processors": [
                    "django.template.context_processors.debug",
                    "django.template.context_processors.request",
                    "django.contrib.auth.context_processors.auth",
                    "django.contrib.messages.context_processors.messages",
                ],
            }},
        }},
    ]

    CACHES = {{
        "default": {{
            "BACKEND": "django.core.cache.backends.memcached.MemcachedCache",
            "LOCATION": ["127.0.0.1:11211"],
        }}
    }}

    ATOMIC_REQUESTS = True


    # SESSION_COOKIE_SECURE = True
    # CSRF_COOKIE_SECURE = True
"""

settings_local = """
    from .base import *


    DEBUG = True
    TEMPLATE_DEBUG = DEBUG

    DATABASES = {{
        "default": {{
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "HOST": "localhost",
            "PORT": "",
            "NAME": "{proj}",
            "USER": "{user}",
            "PASSWORD": get_env_variable("DJANGO_DB_PASSWORD"),
        }}
    }}

    INSTALLED_APPS += ("debug_toolbar", )
    MIDDLEWARE_CLASSES += ("debug_toolbar.middleware.DebugToolbarMiddleware", )
"""

settings_staging = """
"""

settings_production = """
    from .base import *


    DEBUG = False
    TEMPLATE_DEBUG = DEBUG

    DATABASES = {{
        "default": {{
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "HOST": "localhost",
            "PORT": "",
            "NAME": "{proj}",
            "USER": "",
            "PASSWORD": "",
        }}
    }}
"""

settings_test = """
"""


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# UWSGI

uwsgi_config = """
    [uwsgi]

    socket = 127.0.0.1:8800
    chdir = {remote_dir}
    module = {proj}.wsgi:application
    virtualenv = {proj}_venv
    master = true
    processes = 5
    max-requests = 4096
    harakiri = 60
    pidfile = pid
    uid = www-data
    gid = www-data
    daemonize = uwsgi.log
    vacuum
"""
# env = DJANGO_SETTINGS_MODULE={proj}.settings.{insta_type}

uwsgi_start = """
    uwsgi --ini config.ini
"""

uwsgi_stop = """
    kill -INT `cat pid`
"""

uwsgi_restart = """
    kill -HUP `cat pid`
"""


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Aux scripts.

s_script = """
    . {proj}_venv/bin/activate
"""

u_script = """
    cd uwsgi
    ./up
    cd -
"""


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


import os
from os import path
import re
from subprocess import call


def prepare_from_4s_formatting(string):
    return re.sub(r"^( {4}|\t)", "", string, flags=re.M).strip() + "\n"


def create_file(file_path):
    with open(file_path, "w") as f:
        f.write("")


def str_to_echo_hex(string):
    return "".join("\\\\" + hex(ord(char))[1:] for char in string)


def setup_django_project(**kwargs):
    proj = kwargs["proj"].strip()
    proj_local_parent_dir = kwargs["proj_local_parent_dir"].strip()
    host = kwargs["host"].strip()
    port = 22 if not kwargs["port"].strip() else int(kwargs["port"])
    user = kwargs["user"].strip()
    ssh_key = kwargs["ssh_key"].strip()
    proj_remote_parent_dir = kwargs["proj_remote_parent_dir"].strip()
    sudo_pass = kwargs["sudo_pass"]
    db_pass = kwargs["db_pass"]
    domain = kwargs["domain"].strip()
    insta_type = kwargs["insta_type"].strip()

    proj_local_dir = path.join(proj_local_parent_dir, proj)
    proj_local_subdir = path.join(proj_local_dir, proj)
    user_host = user + "@" + host
    if not proj_remote_parent_dir.endswith("/"):  # assuming UNIX
        proj_remote_dir = proj_remote_parent_dir + "/" + proj
    else:
        proj_remote_dir = proj_remote_parent_dir + proj

    if not path.exists(proj_local_dir):
        os.mkdir(proj_local_dir)

    if not path.exists(proj_local_subdir):
        os.mkdir(proj_local_subdir)

    create_file(path.join(proj_local_subdir, "README.md"))
    create_file(path.join(proj_local_subdir, ".gitignore"))

    # Requirements.
    req_dir = path.join(proj_local_subdir, "requirements")
    if not path.exists(req_dir):
        os.mkdir(req_dir)
    with open(path.join(req_dir, req_base_fn), "w") as f:
        f.write(prepare_from_4s_formatting(req_base))
    with open(path.join(req_dir, req_local_fn), "w") as f:
        f.write(prepare_from_4s_formatting(req_local))
    with open(path.join(req_dir, req_staging_fn), "w") as f:
        f.write(prepare_from_4s_formatting(req_staging))
    with open(path.join(req_dir, req_production_fn), "w") as f:
        f.write(prepare_from_4s_formatting(req_production))

    port_substr = " -i $sshkey"

    # Shell scripts.
    script = prepare_from_4s_formatting(sync_script)
    if not ssh_key:
        script = script.replace(port_substr, "")
    script = script.\
        format(proj=proj,
               ssh_key=ssh_key,
               remote_parent_dir=proj_remote_parent_dir,
               remote_dir=proj_remote_dir,
               user_host=user_host,
               port=port,
               user=user)
    with open(path.join(proj_local_dir, sync_script_fn), "w") as f:
        f.write(script)
    #
    script = prepare_from_4s_formatting(restart_uwsgi_script)
    if not ssh_key:
        script = script.replace(port_substr, "")
    script = script.\
        format(ssh_key=ssh_key,
               remote_dir=proj_remote_dir,
               user_host=user_host,
               port=port,
               proj=proj)
    with open(path.join(proj_local_dir, restart_uwsgi_script_fn), "w") as f:
        f.write(script)
    #
    script = prepare_from_4s_formatting(sync_back_script)
    if not ssh_key:
        script = script.replace(port_substr, "")
    script = script.\
        format(remote_dir=proj_remote_dir,
               user_host=user_host,
               port=port,
               ssh_key=ssh_key,
               proj=proj)
    with open(path.join(proj_local_dir, sync_back_script_fn), "w") as f:
        f.write(script)
    #
    script = prepare_from_4s_formatting(make_migrations_script)
    if not ssh_key:
        script = script.replace(port_substr, "")
    script = script.\
        format(ssh_key=ssh_key,
               remote_dir=proj_remote_dir,
               user_host=user_host,
               port=port,
               proj=proj)
    with open(path.join(proj_local_dir, make_migrations_script_fn), "w") as f:
        f.write(script)
    #
    script = prepare_from_4s_formatting(make_migrations_and_migrate_script)
    if not ssh_key:
        script = script.replace(port_substr, "")
    script = script.\
        format(ssh_key=ssh_key,
               remote_dir=proj_remote_dir,
               user_host=user_host,
               port=port,
               proj=proj)
    with open(path.join(proj_local_dir, make_migrations_and_migrate_script_fn), "w") as f:
        f.write(script)
    #
    script = prepare_from_4s_formatting(server_shell_script)
    if not ssh_key:
        script = script.replace(port_substr, "")
    script = script.\
        format(ssh_key=ssh_key,
               remote_dir=proj_remote_dir,
               user_host=user_host,
               port=port)
    with open(path.join(proj_local_dir, server_shell_script_fn), "w") as f:
        f.write(script)

    # Sublime Text project.
    script = prepare_from_4s_formatting(sublime_project)
    if not ssh_key:
        script = script.replace(port_substr, "")
    script = script.\
        format(proj=proj,
               port=port,
               ssh_key=ssh_key,
               user_host=user_host,
               domain=domain)
    with open(path.join(proj_local_dir, "{}.sublime-project".format(proj)), "w") as f:
        f.write(script)

    chmod_script_fns = (
        sync_script_fn,
        restart_uwsgi_script_fn,
        sync_back_script_fn,
        make_migrations_script_fn,
        make_migrations_and_migrate_script_fn,
        server_shell_script_fn,
    )
    for script_fn in chmod_script_fns:
        script_fp = path.join(proj_local_dir, script_fn)
        call("chmod a+x {}".format(script_fp), shell=True)

    proj_core_dir = path.join(proj_local_subdir, proj)
    if not path.exists(proj_core_dir):
        os.mkdir(proj_core_dir)

    # Settings.
    settings_dir = path.join(proj_core_dir, "settings")
    if not path.exists(settings_dir):
        os.mkdir(settings_dir)
    create_file(path.join(settings_dir, "__init__.py"))
    #
    settings = prepare_from_4s_formatting(settings_base)
    settings = settings.\
        format(domain=domain,
               proj=proj)
    with open(path.join(settings_dir, "base.py"), "w") as f:
        f.write(settings)
    #
    settings = prepare_from_4s_formatting(settings_local)
    settings = settings.\
        format(proj=proj,
               user=user)
    with open(path.join(settings_dir, "local.py"), "w") as f:
        f.write(settings)
    #
    settings = prepare_from_4s_formatting(settings_staging)
    settings = settings.format()
    with open(path.join(settings_dir, "staging.py"), "w") as f:
        f.write(settings)
    #
    settings = prepare_from_4s_formatting(settings_production)
    settings = settings.format(proj=proj)
    with open(path.join(settings_dir, "production.py"), "w") as f:
        f.write(settings)
    #
    settings = prepare_from_4s_formatting(settings_test)
    settings = settings.format()
    with open(path.join(settings_dir, "test.py"), "w") as f:
        f.write(settings)

    # UWSGI.
    uwsgi_dir = path.join(proj_local_subdir, "uwsgi")
    if not path.exists(uwsgi_dir):
        os.mkdir(uwsgi_dir)
    #
    uwsgi = prepare_from_4s_formatting(uwsgi_config)
    uwsgi = uwsgi.\
        format(remote_dir=proj_remote_dir,
               proj=proj)
    with open(path.join(uwsgi_dir, "config.ini"), "w") as f:
        f.write(uwsgi)
    #
    uwsgi = prepare_from_4s_formatting(uwsgi_start)
    with open(path.join(uwsgi_dir, "up"), "w") as f:
        f.write(uwsgi)
    #
    uwsgi = prepare_from_4s_formatting(uwsgi_stop)
    with open(path.join(uwsgi_dir, "down"), "w") as f:
        f.write(uwsgi)
    #
    uwsgi = prepare_from_4s_formatting(uwsgi_restart)
    with open(path.join(uwsgi_dir, "re"), "w") as f:
        f.write(uwsgi)

    # Aux scripts.
    script = prepare_from_4s_formatting(s_script)
    script = script.format(proj=proj)
    with open(path.join(proj_local_subdir, "s"), "w") as f:
        f.write(script)
    #
    script = prepare_from_4s_formatting(u_script)
    with open(path.join(proj_local_subdir, "u"), "w") as f:
        f.write(script)

    templates_dir = path.join(proj_local_subdir, "templates")
    if not path.exists(templates_dir):
        os.mkdir(templates_dir)

    # Sync forward.
    call("/bin/bash {}".format(path.join(proj_local_dir, sync_script_fn)), shell=True)

    remote_cmd = """
        echo -e {sudo_pass} | sudo -S apt-get update
        echo -e {sudo_pass} | sudo -S pip3 install virtualenv
        cd {remote_dir}
        virtualenv {proj}_venv
        . {proj}_venv/bin/activate
        pip install -r requirements/{insta_type}.txt
        django-admin startproject {proj} .
        mkdir staticroot
        mkdir mediaroot
        chmod u+x s u
        cd uwsgi
        chmod u+x up down re
        deactivate
    """.format(sudo_pass=str_to_echo_hex(sudo_pass),
               remote_dir=proj_remote_dir,
               proj=proj,
               insta_type=insta_type)
    remote_cmd = re.sub(r"^( +|\t+)", "", remote_cmd, flags=re.M).strip()
    remote_cmd = re.sub(r"\r\n|\n", " && ", remote_cmd)
    remote_cmd = "'{}'".format(remote_cmd)
    if ssh_key:
        cmd = "ssh -i {ssh_key} -p {port} {user_host} {remote_cmd}".\
            format(ssh_key=ssh_key,
                   port=port,
                   user_host=user_host,
                   remote_cmd=remote_cmd)
    else:
        cmd = "ssh -p {port} {user_host} {remote_cmd}".\
            format(port=port,
                   user_host=user_host,
                   remote_cmd=remote_cmd)
    call(cmd, shell=True)

    # Sync backward.
    sync_excl_fmt = sync_excl.format(proj=proj)
    if ssh_key:
        cmd = (
            "rsync -az {sync_excl} -e 'ssh -i {ssh_key} -p {port}' {user_host}:{remote_dir} "
            "{local_dir}").\
            format(sync_excl=sync_excl_fmt,
                   ssh_key=ssh_key,
                   port=port,
                   user_host=user_host,
                   remote_dir=proj_remote_dir,
                   local_dir=proj_local_dir)
    else:
        cmd = "rsync -az {sync_excl} -e 'ssh -p {port}' {user_host}:{remote_dir} {local_dir}".\
            format(sync_excl=sync_excl_fmt,
                   port=port,
                   user_host=user_host,
                   remote_dir=proj_remote_dir,
                   local_dir=proj_local_dir)
    call(cmd, shell=True)

    # Extract the secret key out of the original settings.
    orig_settings_fp = path.join(proj_core_dir, "settings.py")
    with open(orig_settings_fp, "r") as f:
        orig_settings = f.read()
    secret_key = re.search(r"SECRET_KEY\s*=\s*[\"'](.+)[\"']", orig_settings).group(1)
    os.remove(orig_settings_fp)

    # Add environment variables.
    env_vars = """
        export PYTHONPATH={remote_dir}
        export DJANGO_SETTINGS_MODULE={proj}.settings.{insta_type}

        export DJANGO_SECRET_KEY='{secret_key}'
        export DJANGO_DB_PASSWORD='{db_pass}'
    """.format(remote_dir=proj_remote_dir,
               proj=proj,
               secret_key=secret_key,
               db_pass=db_pass,
               insta_type=insta_type)
    env_vars = "\n\n" + re.sub(r"^( +|\t+)", "", env_vars, flags=re.M).strip()
    env_vars = str_to_echo_hex(env_vars)
    remote_cmd = "'echo -e {env_vars} >> {remote_dir}/{proj}_venv/bin/activate'".\
        format(env_vars=env_vars,
               remote_dir=proj_remote_dir,
               proj=proj)
    if ssh_key:
        cmd = "ssh -i {ssh_key} -p {port} {user_host} {remote_cmd}".\
            format(ssh_key=ssh_key,
                   port=port,
                   user_host=user_host,
                   remote_cmd=remote_cmd)
    else:
        cmd = "ssh -p {port} {user_host} {remote_cmd}".\
            format(port=port,
                   user_host=user_host,
                   remote_cmd=remote_cmd)
    call(cmd, shell=True)

    # manage.py
    manage_fp = path.join(proj_local_subdir, "manage.py")
    with open(manage_fp, "r") as f:
        manage = f.read()
        # manage = manage.replace("{}.settings".format(proj), "{}.settings.{}".format(proj, insta_type))
        manage = re.sub(
            r"^\s+os\.environ\.setdefault\(\"DJANGO_SETTINGS_MODULE\".*\n+",
            "", manage, flags=re.M)
    with open(manage_fp, "w") as f:
        f.write(manage)

    # wsgi.py
    wsgi_fp = path.join(proj_core_dir, "wsgi.py")
    with open(wsgi_fp, "r") as f:
        wsgi = f.read()
        # wsgi = wsgi.replace("{}.settings".format(proj), "{}.settings.{}".format(proj, insta_type))
        wsgi = re.sub(
            r"^\s+os\.environ\.setdefault\(\"DJANGO_SETTINGS_MODULE\".*\n",
            "", wsgi, flags=re.M)
    with open(wsgi_fp, "w") as f:
        f.write(wsgi)

    # Sync forward.
    call("/bin/bash {}".format(path.join(proj_local_dir, sync_script_fn)), shell=True)


from platform import system as platform
from os import system
from tkinter import Tk, BOTH, X, RIGHT, FLAT, END, filedialog
from tkinter.ttk import Frame, Button, Label, Entry, Style


class MainFrame(Frame):

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.parent.title("InstaDjango")

        self.pack(fill=BOTH, expand=1)
        self.size_and_center_window()

        self.style = Style()
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="#808080", foreground="white")
        self.style.configure("TButton", background="#808080", foreground="white")
        self.style.configure("high.TButton", background="#8FBC8B", foreground="white")
        self.style.configure("TLabel", background="#808080", foreground="white")
        self.style.map("TButton", background=[("pressed", "#404040"), ("active", "#A0A0A0")])

        frame = Frame(self, relief=FLAT, borderwidth=1)
        frame.pack(fill=BOTH, expand=1)

        subframe_0 = Frame(frame, relief=FLAT, borderwidth=0)
        subframe_0.pack(fill=X)
        lbl_0 = Label(subframe_0, text="App's machine-readable name (used for naming folders locally and remotely):", style="TLabel")
        lbl_0.pack(fill=BOTH, padx=10, pady=10)
        entry_0 = Entry(subframe_0)
        entry_0.pack(fill=X, padx=10, ipady=5)
        self.set_entry_text(entry_0, "")

        subframe_1 = Frame(frame, relief=FLAT, borderwidth=0)
        subframe_1.pack(fill=X)
        lbl_1 = Label(
            subframe_1, text="Where to create the app's folder locally:", style="TLabel")
        lbl_1.pack(fill=BOTH, padx=10, pady=10)
        entry_1 = Entry(subframe_1)

        def action_1():
            cdir = filedialog.askdirectory(title="Please select a directory")
            if cdir:
                self.set_entry_text(entry_1, cdir)

        button_1 = Button(subframe_1, text="Choose", command=action_1, style="TButton")
        button_1.pack(side=RIGHT, padx=10, pady=0)
        entry_1.pack(fill=X, padx=10, ipady=5)
        self.set_entry_text(entry_1, "")

        subframe_2 = Frame(frame, relief=FLAT, borderwidth=0)
        subframe_2.pack(fill=X)
        lbl_2 = Label(subframe_2, text="Remote host:", style="TLabel")
        lbl_2.pack(fill=BOTH, padx=10, pady=10)
        entry_2 = Entry(subframe_2)
        entry_2.pack(fill=X, padx=10, ipady=5)
        self.set_entry_text(entry_2, "")

        subframe_3 = Frame(frame, relief=FLAT, borderwidth=0)
        subframe_3.pack(fill=X)
        lbl_3 = Label(
            subframe_3, text="Remote SSH port (empty will mean the default port):", style="TLabel")
        lbl_3.pack(fill=BOTH, padx=10, pady=10)
        entry_3 = Entry(subframe_3)
        entry_3.pack(fill=X, padx=10, ipady=5)
        self.set_entry_text(entry_3, "")

        subframe_4 = Frame(frame, relief=FLAT, borderwidth=0)
        subframe_4.pack(fill=X)
        lbl_4 = Label(subframe_4, text="Remote user:", style="TLabel")
        lbl_4.pack(fill=BOTH, padx=10, pady=10)
        entry_4 = Entry(subframe_4)
        entry_4.pack(fill=X, padx=10, ipady=5)
        self.set_entry_text(entry_4, "")

        subframe_5 = Frame(frame, relief=FLAT, borderwidth=0)
        subframe_5.pack(fill=X)
        lbl_5 = Label(
            subframe_5, text="Local path to the SSH private key:", style="TLabel")
        lbl_5.pack(fill=BOTH, padx=10, pady=10)
        entry_5 = Entry(subframe_5)

        def action_5():
            cdir = filedialog.askopenfilename(title="Please select a private key")
            if cdir:
                self.set_entry_text(entry_5, cdir)

        button_5 = Button(subframe_5, text="Choose", command=action_5, style="TButton")
        button_5.pack(side=RIGHT, padx=10, pady=0)
        entry_5.pack(fill=X, padx=10, ipady=5)
        self.set_entry_text(entry_5, "")

        subframe_6 = Frame(frame, relief=FLAT, borderwidth=0)
        subframe_6.pack(fill=X)
        lbl_6 = Label(
            subframe_6, text="Where to create the app's folder remotely (should not be owned by root):", style="TLabel")
        lbl_6.pack(fill=BOTH, padx=10, pady=10)
        entry_6 = Entry(subframe_6)
        entry_6.pack(fill=X, padx=10, ipady=5)
        self.set_entry_text(entry_6, "/var/www")

        subframe_7 = Frame(frame, relief=FLAT, borderwidth=0)
        subframe_7.pack(fill=X)
        lbl_7 = Label(subframe_7, text="Sudo password:", style="TLabel")
        lbl_7.pack(fill=BOTH, padx=10, pady=10)
        entry_7 = Entry(subframe_7, show="*")
        entry_7.pack(fill=X, padx=10, ipady=5)
        self.set_entry_text(entry_7, "")

        subframe_8 = Frame(frame, relief=FLAT, borderwidth=0)
        subframe_8.pack(fill=X)
        lbl_8 = Label(subframe_8, text="Database password:", style="TLabel")
        lbl_8.pack(fill=BOTH, padx=10, pady=10)
        entry_8 = Entry(subframe_8, show="*")
        entry_8.pack(fill=X, padx=10, ipady=5)
        self.set_entry_text(entry_8, "")

        subframe_9 = Frame(frame, relief=FLAT, borderwidth=0)
        subframe_9.pack(fill=X)
        lbl_9 = Label(subframe_9, text="Domain:", style="TLabel")
        lbl_9.pack(fill=BOTH, padx=10, pady=10)
        entry_9 = Entry(subframe_9)
        entry_9.pack(fill=X, padx=10, ipady=5)
        self.set_entry_text(entry_9, "dev.example.com")

        subframe_10 = Frame(frame, relief=FLAT, borderwidth=0)
        subframe_10.pack(fill=X)
        lbl_10 = Label(subframe_10, text="Django installation type (local, production, staging):", style="TLabel")
        lbl_10.pack(fill=BOTH, padx=10, pady=10)
        entry_10 = Entry(subframe_10)
        entry_10.pack(fill=X, padx=10, ipady=5)
        self.set_entry_text(entry_10, "local")

        def go():
            setup_django_project(
                proj=entry_0.get(),
                proj_local_parent_dir=entry_1.get(),
                host=entry_2.get(),
                port=entry_3.get(),
                user=entry_4.get(),
                ssh_key=entry_5.get(),
                proj_remote_parent_dir=entry_6.get(),
                sudo_pass=entry_7.get(),
                db_pass=entry_8.get(),
                domain=entry_9.get(),
                insta_type=entry_10.get())
            self.quit()
        inst_button = Button(self, text="Go", command=go, style="high.TButton")
        inst_button.pack(side=RIGHT, padx=10, pady=10)

        quit_button = Button(self, text="Quit", command=self.quit, style="TButton")
        quit_button.pack(side=RIGHT, pady=10)

    def size_and_center_window(self):
        w = 640
        h = 850
        sw = self.parent.winfo_screenwidth()
        sh = self.parent.winfo_screenheight()
        x = (sw - w)/2
        y = (sh - h)/2
        self.parent.geometry("%dx%d+%d+%d" % (w, h, x, y))

    @staticmethod
    def set_entry_text(e, text):
        e.delete(0, END)
        e.insert(0, text)


root = Tk()
frame = MainFrame(root)
if platform() == "Darwin":
    system(
        "/usr/bin/osascript -e 'tell app \"Finder\" to set frontmost of process \"Python\" to "
        "true'")
root.mainloop()
