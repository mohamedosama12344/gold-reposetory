pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        IMAGE_NAME      = 'gold-dashboard'
        CONTAINER_NAME  = 'gold-dashboard'
        HOST_PORT       = '5050'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build image') {
            steps {
                sh 'docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} -t ${IMAGE_NAME}:latest .'
            }
        }

        stage('Deploy') {
            steps {
                // Stop/remove any previous container, then start the new one
                // with --restart unless-stopped so it survives reboots and
                // crashes even though Jenkins itself isn't keeping it alive.
                sh '''
                    docker rm -f ${CONTAINER_NAME} || true
                    docker run -d \
                        --name ${CONTAINER_NAME} \
                        --restart unless-stopped \
                        -p ${HOST_PORT}:5000 \
                        ${IMAGE_NAME}:latest
                '''
            }
        }

        stage('Verify it stayed up') {
            steps {
                // Check from inside the app container itself — Jenkins runs
                // in its own container, so "localhost" there isn't the same
                // network namespace as the host's published port.
                sh '''
                    sleep 3
                    docker exec ${CONTAINER_NAME} python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/healthz')"
                '''
            }
        }
    }

    post {
        success {
            echo "Gold dashboard running at http://<host>:${HOST_PORT} (container: ${CONTAINER_NAME}, restart policy: unless-stopped)"
        }
        failure {
            echo 'Deploy failed — check: docker logs gold-dashboard'
        }
    }
}
