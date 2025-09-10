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
    REGISTRY = 'docker.io/mudam5'
    IMAGE_PREFIX = 'log'
    IMAGE_TAG = 'latest'
    COMPOSE_FILES = "-f docker-compose.local.yml -f docker-compose.cloud.yml"
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

    stage('Docker Login') {
      steps {
        ansiColor('xterm') {
          withCredentials([usernamePassword(credentialsId: 'docker', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
            sh '''
              echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
            '''
          }
        }
      }
    }

    stage('Build Images') {
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

            def branches = [:]
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
                        .
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
            def services = [
              'log-collector',
              'log-generator',
              'log-listener',
              'log-ui',
              'persistor-application',
              'persistor-auth',
              'persistor-payment',
              'persistor-system'
            ]

            services.each { svcName ->
              sh """
                REPO_BASE="${REGISTRY}/${IMAGE_PREFIX}-${svcName}"
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
            docker compose -p "${PROJECT_NAME}" ${COMPOSE_FILES} up -d --no-build --remove-orphans
            docker compose -p "${PROJECT_NAME}" ${COMPOSE_FILES} ps
          """
        }
      }
    }

    stage('Smoke Check') {
      steps {
        ansiColor('xterm') {
          sh """
            docker compose -p "${PROJECT_NAME}" ${COMPOSE_FILES} logs --no-color --tail=100 || true
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
        echo "❌ Build/Deploy failed. Dumping logs..."
        sh """
          docker compose -p "${PROJECT_NAME}" ${COMPOSE_FILES} ps || true
          docker compose -p "${PROJECT_NAME}" ${COMPOSE_FILES} logs --no-color --tail=200 || true
        """
      }
    }
    always {
      ansiColor('xterm') {
        sh 'docker system df || true'
      }
    }
  }
}
