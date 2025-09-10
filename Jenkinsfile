pipeline {
  agent any

  options {
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '20'))
    disableConcurrentBuilds()
  }

  environment {
    DOCKER_BUILDKIT = '1'
    DEPLOY_ENV = 'local'
    REGISTRY = 'docker.io/myuser'
    IMAGE_PREFIX = 'log'
    IMAGE_TAG = 'latest'
    COMPOSE_FILE = "docker-compose.local.yml"
    PROJECT_NAME = "log-generator-local"
  }

  stages {
    stage('Checkout') {
      steps {
        ansiColor('xterm') {
          checkout scm
        }
      }
    }

    stage('Prepare') {
      steps {
        ansiColor('xterm') {
          script {
            def services = [
              [name: 'log-collector',         context: 'log-collector',         dockerfile: 'Dockerfile'],
              [name: 'log-generator',         context: 'log-generator',         dockerfile: 'Dockerfile'],
              [name: 'log-listener',          context: 'log-listener',          dockerfile: 'Dockerfile'],
              [name: 'log-ui',                context: 'log-ui',                dockerfile: 'Dockerfile'],
              [name: 'persistor-application', context: 'persistor-application', dockerfile: 'Dockerfile'],
              [name: 'persistor-auth',        context: 'persistor-auth',        dockerfile: 'Dockerfile'],
              [name: 'persistor-payment',     context: 'persistor-payment',     dockerfile: 'Dockerfile'],
              [name: 'persistor-system',      context: 'persistor-system',      dockerfile: 'Dockerfile']
            ]
            env.services = services
            sh """ test -f "${COMPOSE_FILE}" || (echo "Missing ${COMPOSE_FILE}" && exit 1) """
          }
        }
      }
    }

    stage('Build Images') {
      steps {
        ansiColor('xterm') {
          script {
            def branches = [:]
            def services = env.services
            services.each { svc ->
              branches[svc.name] = {
                catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                  dir(svc.context) {
                    sh """
                      echo '🔧 Building service: ${svc.name}'
                      REPO_BASE="${REGISTRY}/${IMAGE_PREFIX}-${svc.name}"
                      echo "Using REPO_BASE: \$REPO_BASE"
                      docker build --pull \
                        -f "${svc.dockerfile}" \
                        -t "\$REPO_BASE:${IMAGE_TAG}" \
                        -t "\$REPO_BASE:latest" \
                        . || (echo "❌ Build failed for ${svc.name}" && exit 1)
                    """
                  }
                }
              }
            }
            parallel branches
          }
        }
      }
    }

    stage('Push Images') {
      steps {
        ansiColor('xterm') {
          script {
            def services = env.services
            services.each { svc ->
              sh """
                REPO_BASE="${REGISTRY}/${IMAGE_PREFIX}-${svc.name}"
                docker push "\$REPO_BASE:${IMAGE_TAG}"
                docker push "\$REPO_BASE:latest"
              """
            }
          }
        }
      }
    }

    stage('Deploy') {
      steps {
        ansiColor('xterm') {
          sh """
            docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" up -d --no-build --remove-orphans
            docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" ps
          """
        }
      }
    }

    stage('Smoke Check') {
      steps {
        ansiColor('xterm') {
          sh """
            docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" logs --no-color --tail=100 || true
          """
        }
      }
    }
  }

  post {
    success {
      ansiColor('xterm') {
        echo "✅ Build and deployment successful for ${PROJECT_NAME}"
      }
    }
    failure {
      ansiColor('xterm') {
        script {
          echo "❌ Build/Deploy failed. Dumping logs..."
          sh """
            docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" ps || true
            docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" logs --no-color --tail=200 || true
          """
        }
      }
    }
    always {
      ansiColor('xterm') {
        sh 'docker system df || true'
      }
    }
  }
}
