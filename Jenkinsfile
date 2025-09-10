pipeline {
  agent any

  options {
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '20'))
    disableConcurrentBuilds()
  }

  parameters {
    choice(
      name: 'DEPLOY_ENV',
      choices: ['local', 'cloud'],
      description: 'Which docker-compose.<env>.yml to use for deploy'
    )
    booleanParam(
      name: 'PUSH_TO_REGISTRY',
      defaultValue: false,
      description: 'If true, tag and push images to a container registry'
    )
    string(
      name: 'REGISTRY',
      defaultValue: '',
      description: 'Registry namespace (e.g., docker.io/<user> or ghcr.io/<owner>). Leave empty for local-only.'
    )
    string(
      name: 'IMAGE_PREFIX',
      defaultValue: 'log',
      description: 'Final repo will be <REGISTRY>/<IMAGE_PREFIX>-<service>'
    )
    string(
      name: 'REGISTRY_CREDENTIALS_ID',
      defaultValue: '',
      description: 'Jenkins credentialsId for registry login (optional)'
    )
  }

  environment {
    DOCKER_BUILDKIT = '1'
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
            env.GIT_SHA = sh(script: "git rev-parse --short=7 HEAD", returnStdout: true).trim()
            env.IMAGE_TAG = "${env.BUILD_NUMBER}-${env.GIT_SHA}"
            env.COMPOSE_FILE = "docker-compose.${params.DEPLOY_ENV}.yml"
            env.PROJECT_NAME = "log-generator-${params.DEPLOY_ENV}"

            services = [
              [name: 'log-collector',         context: 'log-collector',         dockerfile: 'Dockerfile'],
              [name: 'log-generator',         context: 'log-generator',         dockerfile: 'Dockerfile'],
              [name: 'log-listener',          context: 'log-listener',          dockerfile: 'Dockerfile'],
              [name: 'log-ui',                context: 'log-ui',                dockerfile: 'Dockerfile'],
              [name: 'persistor-application', context: 'persistor-application', dockerfile: 'Dockerfile'],
              [name: 'persistor-auth',        context: 'persistor-auth',        dockerfile: 'Dockerfile'],
              [name: 'persistor-payment',     context: 'persistor-payment',     dockerfile: 'Dockerfile'],
              [name: 'persistor-system',      context: 'persistor-system',      dockerfile: 'Dockerfile'],
            ]

            sh """ test -f "${env.COMPOSE_FILE}" || (echo "Missing ${env.COMPOSE_FILE}" && exit 1) """

            echo """
            Build context:
              DEPLOY_ENV       = ${params.DEPLOY_ENV}
              COMPOSE_FILE     = ${env.COMPOSE_FILE}
              PROJECT_NAME     = ${env.PROJECT_NAME}
              IMAGE_TAG        = ${env.IMAGE_TAG}
              PUSH_TO_REGISTRY = ${params.PUSH_TO_REGISTRY}
              REGISTRY         = ${params.REGISTRY}
              IMAGE_PREFIX     = ${params.IMAGE_PREFIX}
            """
          }
        }
      }
    }

    stage('Docker Login (optional)') {
      when {
        expression { params.PUSH_TO_REGISTRY && params.REGISTRY?.trim() && params.REGISTRY_CREDENTIALS_ID?.trim() }
      }
      steps {
        ansiColor('xterm') {
          withCredentials([usernamePassword(
            credentialsId: params.REGISTRY_CREDENTIALS_ID,
            usernameVariable: 'REG_USER',
            passwordVariable: 'REG_PASS'
          )]) {
            sh '''
              set -e
              REG_HOST="${REGISTRY%%/*}"
              if [ -z "$REG_HOST" ]; then
                echo "Cannot derive registry host from REGISTRY=${REGISTRY}"
                exit 1
              fi
              echo "$REG_PASS" | docker login "$REG_HOST" --username "$REG_USER" --password-stdin
            '''
          }
        }
      }
    }

    stage('Build Images (per service, parallel)') {
      steps {
        ansiColor('xterm') {
          script {
            def branches = [:]
            services.each { svc ->
              branches[svc.name] = {
                dir(svc.context) {
                  sh """
                    set -euxo pipefail
                    REPO_BASE="${params.REGISTRY?.trim() ? params.REGISTRY + '/' : ''}${params.IMAGE_PREFIX}-${svc.name}"
                    docker build --pull \
                      -f "${svc.dockerfile}" \
                      -t "${REPO_BASE}:${env.IMAGE_TAG}" \
                      -t "${REPO_BASE}:latest" \
                      .
                  """
                }
              }
            }
            parallel branches
          }
        }
      }
    }

    stage('Push Images (optional)') {
      when { expression { params.PUSH_TO_REGISTRY && params.REGISTRY?.trim() } }
      steps {
        ansiColor('xterm') {
          script {
            services.each { svc ->
              sh """
                set -euxo pipefail
                REPO_BASE="${params.REGISTRY}/${params.IMAGE_PREFIX}-${svc.name}"
                docker push "${REPO_BASE}:${env.IMAGE_TAG}"
                docker push "${REPO_BASE}:latest"
              """
            }
          }
        }
      }
    }

    stage('Deploy (docker compose up -d)') {
      steps {
        ansiColor('xterm') {
          sh """
            set -euxo pipefail
            export REGISTRY="${params.REGISTRY}"
            export IMAGE_PREFIX="${params.IMAGE_PREFIX}"
            export IMAGE_TAG="${env.IMAGE_TAG}"

            docker compose -p "${env.PROJECT_NAME}" -f "${env.COMPOSE_FILE}" up -d --no-build --remove-orphans
            docker compose -p "${env.PROJECT_NAME}" -f "${env.COMPOSE_FILE}" ps
          """
        }
      }
    }

    stage('Smoke Check (basic)') {
      steps {
        ansiColor('xterm') {
          sh '''
            set -euxo pipefail
            docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" logs --no-color --tail=100 || true
          '''
        }
      }
    }
  }

  post {
    success {
      ansiColor('xterm') {
        echo "✅ Built per-service Docker images and deployed ${env.PROJECT_NAME} with tag ${env.IMAGE_TAG}"
      }
    }
    failure {
      ansiColor('xterm') {
        script {
          echo "❌ Build/Deploy failed. Dumping compose status & recent logs…"
          sh '''
            docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" ps || true
            docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" logs --no-color --tail=200 || true
          '''
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
