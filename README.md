# Expanse: the limitless Python web framework

Expanse is a **modern** and **elegant** web application framework.

At the heart of its design and architecture is and always will be the **developer experience**.
Expanse wants to get out of your way and let you build what matters by giving you intuitive and powerful tools
like transparent **dependency injection**, a **powerful database component** (powered
by [SQLAlchemy](https://www.sqlalchemy.org/)),
**queues** (_Coming soon_), **authentication** (_Coming soon_), **authorization** (_Coming soon_), and more.

## Installation

To leverage all Expanse has to offer, it is best to setup your project with the official installer. The installer
creates the project with a convention-based structure that lets you start implementing features right away.

Before creating your first project, make sure that you have Python (minimum version: 3.10) installed on your machine
along with [`pipx`](https://pipx.pypa.io/stable/).

Once both are installed, you can use the official [Expanse installer](https://github.com/expanse-framework/installer)
to create your project:

```bash
pipx install expanse-installer

expanse new my-app
```

Now that you project is created, you can start the development server via the Craft `serve` command:

```bash
cd my-app

./beam serve
```

Your application is now available at [http://localhost:8000](http://localhost:8000), and you are ready to start building
you project.

## Documentation

[Documentation] for the current version of Expanse (as well as the development branch and recently out of support
versions) is available from the [official website](https://expanse-framework.com).

## Contribute

Expanse is a large, complex project always in need of contributors. For those new to the project, a list of
[suggested issues] to work on is available. The full [contributing documentation] also
provides helpful guidance.

## Resources

* [Releases][PyPI Releases]
* [Official Website]
* [Documentation]
* [Issue Tracker]

  [PyPI]: https://pypi.org/project/expanse/

  [PyPI Releases]: https://pypi.org/project/expanse/#history

  [Official Website]: https://expanse-framework.com

  [Documentation]: https://expanse-framework.com/docs

  [Issue Tracker]: https://github.com/expanse-framework/expanse/issues

  [Suggested Issues]: https://github.com/expanse-framework/expanse/contribute

  [Contributing Documentation]: https://expanse-framework.com/docs/contributing

  [Installation Documentation]: https://expanse-framework.com/docs/#installation

## Related Projects

* [expanse-installer](https://github.com/expanse-framework/installer): The official installer for Expanse projects. It
  will
  setup a ready-to-be-used project for you.
* [website](https://github.com/expanse-framework/expanse-framework.com): The official Poetry website.
