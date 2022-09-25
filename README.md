<!-- # running-routes -->
<header>
<div>
<img src="docs/logo.jpeg" width="100px"> 
<font size="70px"><a href="www.running-routes.com">running-routes</a> </font>
</div>
</header>

---
## Aim
* Create running routes to aid training (Melbourne Marathon 2022)
* Apply data science and optimisation techniques to geospatial data
* Contribute to the open-source and open-data community
* Learn some front-end dev

## Architecture
```mermaid
graph 
    subgraph GitHub
    github_code(Repository)
    github_actions(GitHub Actions)
    github_pages(GitHub Pages)
    end

    subgraph Google
    google_registry(Google Registry)
    google_cloud_run(Cloud Run)
    end
    
    subgraph DockerHub
    dockerhub_image(Images)
    end
    
    github_code -- Trigger CI/CD pipelines --> github_actions
    google_registry -- Reference image --> google_cloud_run
    github_actions -- Build and push --> google_registry
    github_actions -- Update definition --> google_cloud_run
    github_actions -- Build and push --> dockerhub_image
    google_cloud_run -- Consume --> github_pages
    github_actions -- Build and deploy --> github_pages

```