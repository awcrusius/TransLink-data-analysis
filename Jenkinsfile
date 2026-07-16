pipeline {
    agent any

    parameters {
        booleanParam(
            name: 'RUN_LIVE_INTEGRATION',
            defaultValue: false,
            description: 'Also run the live TransLink API integration tests (requires the translink-api-key credential and consumes API quota).'
        )
    }

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '30'))
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt -r requirements-dev.txt
                '''
            }
        }

        stage('Unit Tests') {
            steps {
                sh '''
                    . .venv/bin/activate
                    pytest gtfs_realtime_container/tests -m "not integration" \
                        --junitxml=test-results/unit.xml
                '''
            }
        }

        stage('Live Integration Tests') {
            when {
                expression { params.RUN_LIVE_INTEGRATION }
            }
            steps {
                // Requires a Jenkins "Secret text" credential with ID
                // translink-api-key containing a real TransLink API key.
                withCredentials([string(credentialsId: 'translink-api-key', variable: 'TRANSLINK_API_KEY')]) {
                    sh '''
                        . .venv/bin/activate
                        pytest gtfs_realtime_container/tests -m integration \
                            --junitxml=test-results/integration.xml
                    '''
                }
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true, testResults: 'test-results/*.xml'
        }
    }
}
