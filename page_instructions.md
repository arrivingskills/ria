# How to Edit Pages in This Website

All page templates live in `src/ria/templates/`.

## Editing an existing page

Open the HTML file for the page you want to change (e.g. `home.html` or `aboutme.html`).

Each page looks like this:

```html
{% extends "base.html" %}

{% block title %}Page Title{% endblock %}

{% block content %}
    <h1>Your Heading</h1>
    <p>Your content goes here.</p>
{% endblock %}
```

- Put your page title inside `{% block title %}...{% endblock %}` (optional — defaults to "Ria").
- Put your page content (headings, paragraphs, images, etc.) inside `{% block content %}...{% endblock %}`.
- You don't need to worry about the navigation menu or the `<html>`/`<head>` tags — `base.html` handles all of that.

## Adding a new page

1. Create a new HTML file in `src/ria/templates/`, e.g. `contact.html`:

    ```html
    {% extends "base.html" %}

    {% block title %}Contact - Ria{% endblock %}

    {% block content %}
        <h1>Contact</h1>
        <p>Get in touch!</p>
    {% endblock %}
    ```

2. Add a route in `src/ria/__init__.py`:

    ```python
    @app.route("/contact")
    def contact():
        return render_template("contact.html")
    ```

3. Add a link in the nav menu in `src/ria/templates/base.html`:

    ```html
    <a href="/contact">Contact</a>
    ```

That's it — your new page will appear in the site with the navigation menu.
