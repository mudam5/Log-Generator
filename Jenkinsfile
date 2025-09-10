pipeline {
  agent any

  options {
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '20'))
    disableConcurrentBuilds()
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
            def deployEnv = 'local'
            def registry = 'docker.io/myuser'
            def imagePrefix = 'log'
            def imageTag = 'latest'
            def composeFile = "docker-compose.${deployEnv}.yml"
            def projectName = "log-generator-${deployEnv}"

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

            writeJSON file: 'pipeline_config.json', json: [
              deployEnv: deployEnv,
              registry: registry,
              imagePrefix: imagePrefix,
              imageTag: imageTag,
              composeFile: composeFile,
              projectName: projectName,
              services: services
            ]
          }
        }
      }
    }

    stage('Build Images') {
      steps {
        ansiColor('xterm') {
          script {
            def config = readJSON file: 'pipeline_config.json'
            def branches = [:]
            for (svc in config.services) {
              def svcName = svc.name
              def svcContext = svc.context
              def svcDockerfile = svc.dockerfile
              branches[svcName] = {
                catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                  dir(svcContext) {
                    sh """
                      echo '🔧 Building service: ${svcName}'
                      REPO_BASE="${config.registry}/${config.imagePrefix}-${svcName}"
                      echo "Using REPO_BASE: \$REPO_BASE"
                      docker build --pull \
                        -f "${svcDockerfile}" \
                        -t "\$REPO_BASE:${config.imageTag}" \
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
            def config = readJSON file: 'pipeline_config.json'
            for (svc in config.services) {
              def svcName = svc.name
              sh """
                REPO_BASE="${config.registry}/${config.imagePrefix}-${svcName}"
                docker push "\$REPO_BASE:${config.imageTag}"
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
          script {
            def config = readJSON file: 'pipeline_config.json'
            sh """
              docker compose -p "${config.projectName}" -f "${config.composeFile}" up -d --no-build --remove-orphans
              docker compose -p "${config.projectName}" -f "${config.composeFile}" ps
            """
          }
        }
      }
    }

    stage('Smoke Check') {
      steps {
        ansiColor('xterm') {
          script {
            def config = readJSON file: 'pipeline_config.json'
            sh """
              docker compose -p "${config.projectName}" -f "${config.composeFile}" logs --no-color --tail=100 || true
            """
          }
        }
      }
    }
  }

  post {
    success {
      ansiColor('xterm') {
        script {
          def config = readJSON file: 'pipeline_config.json'
          echo "✅ Build and deployment successful for ${config.projectName}"
        }
      }
    }
    failure {
      ansiColor('xterm') {
        script {
          def config = readJSON file: 'pipeline_config.json'
          echo "❌ Build/Deploy failed. Dumping logs..."
          sh """
            docker compose -p "${config.projectName}" -f "${config.composeFile}" ps || true
            docker compose -p "${config.projectName}" -f "${config.composeFile}" logs --no-color --tail=200 || true
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
