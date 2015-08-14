# InstaDjango

Some web app ideas just can't wait. All you want to do is to start developing ASAP without going through a tedious and potentially erroneous installation process of your web framework.

And if your favorite web framework happens to be Django, which is one of the most proficiently crafted and easy to use frameworks there are, InstaDjango might be exactly what you need to spin up a Django server in the matter of seconds.

<p align="center">
  <img src="readme_files/gui.png"/>
</p>

## Features

InstaDjango takes care of:

* **virtualenv**: as a standard practice, your app is installed into its own virtual environment
* **uWSGI**: this communication layer between the web server and Django, which is recommended by Django developers, is installed and configured for your app automatically, providing you with easy ways to start up, shut down, and restart uWSGI
* **your app's requirements**
* **directory structures**: the files of your app are conveniently organized according to a highly reputable "[Two Scoops of Django: Best Practices for Django](http://twoscoopspress.org/products/two-scoops-of-django-1-8)"
* **deployment profiles**: app requirements and setting are split and logically chained to let you deploy your app for local development, production, staging (pre-production), or testing
* **your initial local copy of the app**: ready to slide under source control, the locally stored directory of your app reflects the relevant files in the remote directory on your server
* **secret key and password security**: unlike with manual installation, the very sensible information such as your app's secret key and your database's password are stored as environment variables in the virtual environment of your app on the server instead of any of the settings file and thereby escape getting accidentally published via source control/collaboration
* **synchronization**: the locally baked rsync-based scripts let you push changes from your local directory into the remote directory and, for example after creating a Django sub-app remotely, pull changes from the remote directory into the local one
* **SSH-ing directly into the app's virtual environment**: no need to first SSH into the server, then go into the app's directory, and then manually activate the virtual environment because a locally prepared script will happily do this all for you
* **Sublime Text integration**: InstaDjango assumes that you are a cool person already using one of the best Python IDEs for your app development, namely Sublime Text powered with Anaconda, so it generates a Sublime Text project pre-configured to push changed into your app's remote directory and restart uWSGI when you simply build the project

## Usage

Just run `InstaDjango.py`, fill out the GUI form, and hit Go. You can make it even faster by hopping through the input fields with the <kbd>Tab</kbd> key!

Before letting it go, make sure that the parent directory where you want the app's remote directory to be created, such as `/var/www`, is owned by the remote user (which is you!) and not root. Otherwise, you may get permission problems.

The domain info is primarily needed for an entry in the Django settings that restricts the app to a specific domain when running in production with `DEBUG` being `false`.

If you are more used to a more straightforward approach to editing source files by means of an FTP/SCP client, for example Cyberduck, instead of using rsync, just remove the local directory and you're done (the remote directory is meant to be a superset of the local one).

After InstaDjango has finished, your app's local directory should look similar to the following structure:

<p align="center">
  <img src="readme_files/local_app_dir.png"/>
</p>

Let's go over the shell scripts that you can notice at the top:

* **[AppShell].command** is for SSH-ing into the server's shell with the working directory changed to the app's remote directory and having the app's virtual environment already activated for you
* **[Push].command** is for pushing changes from the local directory into the remote one; you may consider running [RestartUwsgi].command after that or simply joining the two scripts together
* **[Pull].command** is for pulling changes from the remote directory into the local one
* **[RestartUwsgi].command** is for restarting uWSGI on the server for the changes to Django files to take effect

Now, let's compare it to the structure of the app's remote directory:

<p align="center">
  <img src="readme_files/remote_app_dir.png"/>
</p>

As you can see, the remote directory contains a directory used by the app's virtual environment, which is technical and has little to do with the functioning of your Django app, while the local directory does not contain this directory to keep things cleaner.

You don't get the directory for static files locally either because static files are supposed to be collected by Django from other directories automatically on the server after you push those files while they are being stored locally inside their respective subdirectories.

## Prerequisites

* OS X with Python 3 locally
* an Ubuntu/Debian server remotely
* a web server, such as Nginx; the configured uWSGI port is expected to be 8800
* PostgreSQL for your server's database (MySQL support might be added later)
* SSH access to the server using a private key and with the passphrase already in the OS X's keychain (if any)
* if you've got Sublime Text, [Anaconda](https://github.com/DamnWidget/anaconda) is to make your Python development more comfortable as well as to facilitate your app's builds with the generated Sublime Text project
