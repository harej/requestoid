from django.db import models

class Requests(models.Model):
    page_id = models.IntegerField()  # Canonical page identifier in MediaWiki
    page_title = models.CharField(max_length=255)  # MediaWiki human-readable page title
    user_id = models.IntegerField()
    user_name = models.CharField(max_length=255)
    wiki = models.CharField(max_length=63)  # Wiki database name
    timestamp = models.CharField(max_length=14)  # MediaWiki-style timestamps, YYYYMMDDHHMMss = 14 chars
    summary = models.CharField(max_length=160)  # Short description of the change to make
    status = models.SmallIntegerField()  # 0 = open; 1 = complete; 2 = declined


class Categories(models.Model):
    request = models.ForeignKey("Requests", on_delete=models.CASCADE)
    cat_id = models.IntegerField()  # Canonical category identifier in MediaWiki
    cat_title = models.CharField(max_length=255)  # MediaWiki human-readable category name (without "Category:")
    wiki = models.CharField(max_length=63)  # Wiki database name
    
    
class WikiProjects(models.Model):
    request = models.ForeignKey("Requests", on_delete=models.CASCADE)
    project_id = models.IntegerField()  # Canonical page identifier in MediaWiki
    project_title = models.CharField(max_length=255)  # MediaWiki human-readable page title    
    wiki = models.CharField(max_length=63)  # Wiki database name

    
class Notes(models.Model):
    request = models.ForeignKey("Requests", on_delete=models.CASCADE)
    user_name = models.CharField(max_length=255)
    user_id = models.IntegerField()
    comment = models.TextField()


class Logs(models.Model):
    request = models.ForeignKey("Requests", on_delete=models.CASCADE)
    user_name = models.CharField(max_length=255)
    user_id = models.IntegerField()
    timestamp = models.CharField(max_length=14)
    action = models.CharField(max_length=255)
